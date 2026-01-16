"""
Tools for working with diff files

TODO: should probably be moved to codeTools or something
"""
import typing
import datetime
from paths import Url
from .difference import Difference,DifferenceType
if typing.TYPE_CHECKING:
    from gitTools.gitCommit import GitCommit
    from .change import ChangeLocation


FileMatch=typing.Union[
    str,
    typing.Pattern[str],
    typing.List[typing.Union[str,typing.Pattern[str]]]]


class FileDifferences:
    """
    Diff of a single file
    """
    def __init__(self,
        data:str,
        commit:typing.Optional["GitCommit"]=None):
        """
        """
        self._data:str=data
        self.url:Url=Url("")
        self.differences:typing.List[Difference]=[]
        self.commit=commit
        self.assign(data)

    def getDifferencesByType(self,
        insertions:bool=True,
        modifications:bool=True,
        deletions:bool=True
        )->typing.Generator[Difference,None,None]:
        """
        Get all differences of a given type
        """
        for difference in self.differences:
            if insertions and difference.differenceType==DifferenceType.TYPE_ADD:
                yield difference
            if modifications and difference.differenceType==DifferenceType.TYPE_MODIFY:
                yield difference
            if deletions and difference.differenceType==DifferenceType.TYPE_REMOVE:
                yield difference

    def getChangeLocations(self,
        insertions:bool=True,
        modifications:bool=True,
        deletions:bool=True,
        before:bool=False,
        after:bool=True
        )->typing.Generator['ChangeLocation',None,None]:
        """
        Get all changes
        """
        # make sure the logic makes sense
        if not before:
            deletions=False
        if not after:
            insertions=False
        for difference in self.getDifferencesByType(insertions,modifications,deletions):
            yield from difference.getChangeLocations(before,after)
    getChanges=getChangeLocations

    @property
    def filename(self)->Url:
        """
        Filename
        """
        return self.url

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
        self.url=Url(data.split(' b/',1)[-1].split('\n',1)[0])
        for s in data.split('\n@@ ')[1:]:
            self.differences.append(Difference(self,'@@ '+s))

    @property
    def numLines(self)->int:
        """
        number of lines affected
        (added,removed,or changed)
        """
        return sum(d.numLines for d in self.differences)

    def asDiffStr(self,
        colorize:typing.Union[None,typing.Literal['ansi'],typing.Literal['html']]=None,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string
        """
        if colorize is None:
            return self.asPlainDiffStr(includeDiffMarkers=includeDiffMarkers)
        elif colorize=='html':
            return self.asAnsiDiffStr(includeDiffMarkers=includeDiffMarkers)
        return self.asHtmlDiffStr(includeDiffMarkers=includeDiffMarkers)

    def asAnsiDiffStr(self,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string with ansi color codes
        """
        from stringTools import ANSI_COLORS
        removed=ANSI_COLORS.ANSI_RED.value
        added=ANSI_COLORS.ANSI_GREEN.value
        off=ANSI_COLORS.ANSI_OFF.value
        filename=str(self.url)
        ret=f'{removed}--- {filename}{off}\n{added}+++ {filename}{off}\n'
        return ret+('\n'.join([d.asAnsiDiffStr(includeDiffMarkers) for d in self.differences]))

    def asHtmlDiffStr(self,
        scopeColor:str="#77c6ff",
        addColor:str="#00FF00",
        removeColor:str="#FF0000",
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string with html colorization
        """
        filename=str(self.url)
        ret=['<div>']
        ret.append(f'<div style="color:{removeColor}">--- {filename}</div>')
        ret.append(f'<div style="color:{addColor}">+++ {filename}</div>')
        ret.extend([
            d.asHtmlDiffStr(scopeColor,addColor,removeColor,includeDiffMarkers)
            for d in self.differences])
        ret.append('</div>')
        return '\n'.join(ret)
    @property
    def html(self)->str:
        """
        Get this as a standard diff string with html colorization
        """
        return self.asHtmlDiffStr()

    def asPlainDiffStr(self,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string
        """
        filename=str(self.url)
        ret=f'--- {filename}\n+++ {filename}\n'
        return ret+('\n'.join([d.asPlainDiffStr(includeDiffMarkers) for d in self.differences]))

    @property
    def diffStr(self)->str:
        """
        Get the difference as a string
        """
        return self.asDiffStr()
    @diffStr.setter
    def diffStr(self,diffStr:str):
        self.assign(diffStr)

    def __str__(self)->str:
        return self.asDiffStr()

    def __repr__(self)->str:
        ret=f'--- {self.url}\n+++ {self.url}'
        return ret+('\n'.join([repr(d) for d in self.differences]))
FileDiff=FileDifferences


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
        self.fileDiffs:typing.Dict[Url,FileDifferences]={}
        self.assign(data)

    def __iter__(self)->typing.Iterator[FileDifferences]:
        return iter(self.fileDiffs.values())

    def getDifferencesByType(self,
        insertions:bool=True,
        modifications:bool=True,
        deletions:bool=True
        )->typing.Generator[Difference,None,None]:
        """
        Get all differences of a given type
        """
        for fileDiff in self.fileDiffs.values():
            yield from fileDiff.getDifferencesByType(insertions,modifications,deletions)

    def getChangeLocations(self,
        insertions:bool=True,
        modifications:bool=True,
        deletions:bool=True,
        before:bool=False,
        after:bool=True
        )->typing.Generator['ChangeLocation',None,None]:
        """
        Get all changes
        """
        for fileDiff in self.fileDiffs.values():
            yield from fileDiff.getChangeLocations(insertions,modifications,deletions,before,after)
    getChanges=getChangeLocations

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
            fd=FileDifferences("diff --git "+f,commit=self.commit)
            setattr(fd,"date",self.date)
            self.fileDiffs[fd.filename]=fd

    @property
    def differences(self)->typing.Generator[Difference,None,None]:
        """
        All of the differences
        """
        for fd in self.fileDiffs.values():
            yield from fd.differences

    @property
    def changedFiles(self)->typing.Generator[Url,None,None]:
        """
        List of all changed files
        """
        yield from self.fileDiffs

    def search(
        self,
        files:FileMatch
        )->typing.Generator[FileDifferences,None,None]:
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

    def asDiffStr(self,
        colorize:typing.Union[None,typing.Literal['ansi'],typing.Literal['html']]=None,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string
        """
        if colorize is None:
            return self.asPlainDiffStr(includeDiffMarkers=includeDiffMarkers)
        elif colorize=='html':
            return self.asAnsiDiffStr(includeDiffMarkers=includeDiffMarkers)
        return self.asHtmlDiffStr(includeDiffMarkers=includeDiffMarkers)

    def asAnsiDiffStr(self,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string with ansi color codes
        """
        return '\n\n'.join([
            fd.asAnsiDiffStr(includeDiffMarkers)
            for fd in self.fileDiffs.values()])

    def asHtmlDiffStr(self,
        scopeColor:str="#77c6ff",
        addColor:str="#00FF00",
        removeColor:str="#FF0000",
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string with html colorization
        """
        return '\n\n'.join([
            fd.asHtmlDiffStr(scopeColor,addColor,removeColor,includeDiffMarkers)
            for fd in self.fileDiffs.values()])
    @property
    def html(self)->str:
        """
        Get this as a standard diff string with html colorization
        """
        return self.asHtmlDiffStr()

    def asPlainDiffStr(self,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string
        """
        return '\n\n'.join([
            fd.asPlainDiffStr(includeDiffMarkers)
            for fd in self.fileDiffs.values()])

    def __repr__(self):
        return '\n\n'.join([repr(k) for k in self.fileDiffs])

    def __str__(self):
        return self.asAnsiDiffStr()
