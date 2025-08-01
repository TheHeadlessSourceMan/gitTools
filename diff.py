"""
Tools for working with diff files

TODO: should probably be moved to codeTools or something
"""
import typing
import datetime
from paths import Url
if typing.TYPE_CHECKING:
    from gitTools.gitCommit import GitCommit


FileMatch=typing.Union[
    str,
    typing.Pattern[str],
    typing.List[typing.Union[str,typing.Pattern[str]]]]


class Difference:
    """
    A single difference within a diff file
    """
    TYPE_NONE=0
    TYPE_ADD=1
    TYPE_REMOVE=2
    TYPE_UPDATE=3

    def __init__(self,data:str):
        self._data:str=data
        self.differenceType:int=self.TYPE_ADD
        self.old:typing.List[str]=[]
        self.new:typing.List[str]=[]
        self.oldContext:typing.List[str]=[]
        self.newContext:typing.List[str]=[]
        self.oldPosition:typing.Tuple[int,int]=(0,0)
        self.newPosition:typing.Tuple[int,int]=(0,0)
        self.scope:str=""
        #self.fileLocation:FileLocation=""
        self.assign(data)

    def assign(self,data:str)->None:
        """
        assign data to this object
        """
        self._data=data
        gotFirstLine=False
        self.differenceType=self.TYPE_NONE
        for line in data.split('\n'):
            if not gotFirstLine:
                if line.startswith('@@ '):
                    locationScope=line.split('@@',2)
                    oldLocationNewLocation=locationScope[1].strip().split()
                    loc=oldLocationNewLocation[0].split(',')
                    self.oldLocation=(int(loc[0][1:]),int(loc[1]))
                    loc=oldLocationNewLocation[1].split(',')
                    self.newLocation=(int(loc[0][1:]),int(loc[1]))
                    self.scope=locationScope[2].strip()
                    gotFirstLine=True
            else:
                if line.startswith('  '): # common context
                    self.oldContext.append(line)
                    self.newContext.append(line)
                elif line.startswith('+ '): # new line
                    self.new.append(line)
                    self.newContext.append(line)
                    self.differenceType|=self.TYPE_ADD
                elif line.startswith('- '): # old line
                    self.old.append(line)
                    self.oldContext.append(line)
                    self.differenceType|=self.TYPE_REMOVE
                elif line.startswith('@@ '): # next diff
                    break
                else: # blank line
                    self.oldContext.append(line)
                    self.newContext.append(line)

    @property
    def numLines(self)->int:
        """
        number of lines affected
        """
        return max(len(self.old),len(self.new))


class FileDiff:
    """
    Diff of a single file
    """
    def __init__(self,
        data:str,
        commit:typing.Optional["GitCommit"]=None):
        """
        """
        self._data:str=data
        self.filename:str=""
        self.differences:typing.List[Difference]=[]
        self.commit=commit
        self.assign(data)

    @property
    def githubUrl(self)->typing.Optional[Url]:
        """
        Remote github url linking this file
        """
        if not self.commit:
            return None
        u=self.commit.githubUrl
        if u is None:
            return None
        u=str(u).split('/commit',1)[0]
        u=f'{u}/blob/{self.commit.hash}/data/{self.filename}'
        return Url(u)

    def assign(self,data:str)->None:
        """
        assign data to this object
        """
        self._data=data
        self.filename=data.split(' b/',1)[-1].split('\n',1)[0]
        for s in data.split('\n@@ ')[1:]:
            self.differences.append(Difference('@@ '+s))

    @property
    def numLines(self)->int:
        """
        number of lines affected
        (added,removed,or changed)
        """
        return sum(d.numLines for d in self.differences)


class MultifileDiff:
    """
    A diff containing multiple files
    """

    def __init__(self,
        data:str,
        date:typing.Optional[datetime.datetime]=None,
        commit:typing.Optional["GitCommit"]=None):
        """
        """
        self.commit=commit
        self._data=data
        self.date=date
        self.fileDiffs:typing.Dict[str,FileDiff]={}
        self.assign(data)

    def __iter__(self)->typing.Iterator[FileDiff]:
        return iter(self.fileDiffs.values())

    @property
    def githubUrl(self)->typing.Optional[Url]:
        """
        remote github link
        """
        if self.commit is None:
            return None
        return self.commit.githubUrl

    def assign(self,data:str)->None:
        """
        assign data to this object
        """
        self._data=data
        for f in data.split("\ndiff --git "):
            fd=FileDiff("diff --git "+f,commit=self.commit)
            setattr(fd,"date",self.date)
            self.fileDiffs[fd.filename]=fd

    @property
    def differences(self)->typing.Generator[Difference,None,None]:
        """
        All of the differences
        """
        for fd in self.fileDiffs.values():
            yield from fd.differences

    def search(
        self,
        files:FileMatch
        )->typing.Generator[FileDiff,None,None]:
        """
        Get only changes for specific files
        """
        if isinstance(files,str) or hasattr(files,"match"):
            files=(files,) # type: ignore
        for fd in self.fileDiffs.values():
            filename=fd.filename
            for m in files: # type: ignore
                if isinstance(m,str):
                    if filename==m:
                        yield fd
                elif m.match(filename) is not None:
                    yield fd

    @property
    def numLines(self)->int:
        """
        number of lines affected
        (added,removed,or changed)
        """
        return sum(fd.numLines for fd in self.fileDiffs.values())

    def __repr__(self):
        return '\n'.join(self.fileDiffs.keys())
