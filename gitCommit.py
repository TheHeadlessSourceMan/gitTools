
"""
Information about a particular git commit
"""
import typing
import datetime


class GitCommit:
    """
    Information about a particular git commit
    """
    def __init__(self,hash:str): # pylint: disable=W0622
        self.hash=hash
        self._lines:typing.List[str]=[]
        self._gatheringLines=False
        self._gatheringDescription=False
        self._date:typing.Optional[datetime.datetime]=None
        self.merge:typing.List[str]=[]
        self.author:str=''
        self.description:str=''

    @property
    def date(self):
        """
        The full date of this commit
        """
        return self.date # TODO: infinite loop!!!
    @date.setter
    def date(self,d:typing.Union[datetime.datetime,str]):
        if isinstance(d,str):
            d=datetime.datetime.strptime(d,r"%a %b %-d %-H:%M:%S %Y %z")
        self._date=d

    @property
    def timestamp(self)->float:
        """
        Timestamp of this commit
        """
        if self._date is None:
            return 0
        return self._date.timestamp()

    # can compare against other GitCommitInfo or a datetime
    def __eq__(self,
        other:typing.Union["GitCommit",datetime.datetime] # type: ignore
        )->bool:
        if isinstance(other,datetime.datetime):
            return other==self._date
        return other.hash==self.hash
    def __lt__(self,other:typing.Union["GitCommit",datetime.datetime])->bool:
        if isinstance(other,datetime.datetime):
            return self._date<other # type: ignore
        return self._date<other._date # type: ignore
    def __gt__(self,other:typing.Union["GitCommit",datetime.datetime])->bool:
        if isinstance(other,datetime.datetime):
            return self._date>other # type: ignore
        return self._date>other._date # type: ignore
    def __le__(self,other:typing.Union["GitCommit",datetime.datetime])->bool:
        if isinstance(other,datetime.datetime):
            return self._date<=other # type: ignore
        return self._date<other._date or self.hash==other.hash # type: ignore
    def __ge__(self,other:typing.Union["GitCommit",datetime.datetime])->bool:
        if isinstance(other,datetime.datetime):
            return self._date>=other # type: ignore
        return self._date>other._date or self.hash==other.hash # type: ignore

    @property
    def comment(self)->str:
        """
        The full comment/description of this commit
        """
        return self.description
    @comment.setter
    def comment(self,comment:str):
        self.description=comment

    @property
    def commitId(self)->str:
        """
        Hash id of this commit
        """
        return self.hash

    @property
    def title(self)->str:
        """
        Title of the commit
        """
        return self.description.replace('\n',' ')

    @property
    def name(self)->str:
        """
        Title of the commit
        """
        return self.title

    @property
    def oldCode(self)->str:
        """
        Return the old code
        """
        ret=[]
        ready=False
        for line in self._lines:
            if not ready:
                if line.startswith('@@'):
                    ready=True
            elif line:
                if line[0]=='+':
                    pass
                elif line[0]=='-':
                    ret.append(line[1:])
                else:
                    ret.append(line)
            else:
                ret.append('')
        return '\n'.join(ret)

    @property
    def newCode(self)->str:
        """
        Return the new code
        """
        ret=[]
        ready=False
        for line in self._lines:
            if not ready:
                if line.startswith('@@'):
                    ready=True
            elif line:
                if line[0]=='+':
                    ret.append(line[1:])
                elif line[0]=='-':
                    pass
                else:
                    ret.append(line)
            else:
                ret.append('')
        return '\n'.join(ret)

    @property
    def diff(self)->str:
        """
        Return a diff describing what this commit did
        """
        return '\n'.join(self._lines)

    @property
    def oneLineSummary(self)->str:
        """
        Return a one-line summary of this commit
        """
        return f'{self.hash} {self.date} ({self.author}) {self.title}'

    def __repr__(self)->str:
        return self.hash
