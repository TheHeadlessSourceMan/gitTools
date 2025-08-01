
"""
Information about a particular git commit
"""
import typing
import datetime
from paths import URL,UrlCompatible,asUrl
from k_runner.osrun import osrun
from .diff import MultifileDiff


class GitCommit:
    """
    Information about a particular git commit
    """
    def __init__(self,
        hash:str, # pylint: disable=W0622
        logEntry:typing.Optional[str]=None,
        githubUrl:typing.Optional[UrlCompatible]=None):
        """ """
        self.hash=hash
        self._githubUrl:typing.Optional[URL]=None
        if githubUrl is not None:
            self._githubUrl=URL(githubUrl)
        self._lines:typing.List[str]=[]
        self._gatheringLines=False
        self._gatheringDescription=False
        self._date:typing.Optional[datetime.datetime]=None
        self.merge:typing.List[str]=[]
        self.author:str=''
        self.authorEmail:str=''
        self.description:str=''
        if logEntry is not None:
            self.assignFromLog(logEntry)

    @property
    def githubUrl(self)->typing.Optional[URL]:
        """
        Remote github link to this commit
        """
        return self._githubUrl
    @githubUrl.setter
    def githubUrl(self,githubUrl:UrlCompatible):
        sp=str(asUrl(githubUrl)).split('/commit',1)[0]
        githubUrl=f"{sp}/commit/{self.hash}"
        self._githubUrl=URL(githubUrl)

    @property
    def localRepoPath(self)->str:
        """
        Where the repo is found
        """
        # TODO: probably have member pointing back to a GitRepo
        # and get it from that
        return '.'

    def clear(self):
        """
        Clear this object
        """
        self.hash:str=""
        self.author:str=""
        self.authorEmail:str=""
        self.date=None

    def assignFromLog(self,logEntry:str):
        """
        Assign from an entry from a git log command
        """
        self.clear()
        for line in logEntry.strip().replace('\r','').split('\n'):
            if line.startswith('commit '):
                self.hash=line.split(' ',1)[1].strip()
            elif line.startswith('Author: '):
                authorStr=line.split(' ',1)[1].strip().split('<',1)
                self.author=authorStr[0].rstrip()
                self.authorEmail=authorStr[1].split('>',1)[0].strip()
            elif line.startswith('Date: '):
                self.date=line.split(' ',1)[1].strip()

    @property
    def date(self)->typing.Optional[datetime.datetime]:
        """
        The full date of this commit
        """
        return self._date
    @date.setter
    def date(self,d:typing.Union[None,datetime.datetime,str]):
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
    def __eq__(self, # type: ignore
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
    def diffText(self)->str:
        """
        Return a diff text string describing what this commit did
        """
        return self.diff._data # pylint: disable=W0212

    @property
    def diff(self)->MultifileDiff:
        """
        Return a diff describing what this commit did
        """
        cmd=f'git diff {self.hash}'
        result=osrun(cmd,workingDirectory=self.localRepoPath)
        return MultifileDiff(result.stdout,self.date,commit=self)

    @property
    def oneLineSummary(self)->str:
        """
        Return a one-line summary of this commit
        """
        return f'{self.hash} {self.date} ({self.author}) {self.title}'

    def __repr__(self)->str:
        return self.hash


def getAllCommits(
    localRepo:str
    )->typing.Generator[GitCommit,None,None]:
    """
    Get all commits for a repo
    """
    cmd="git log"
    results=osrun(cmd,workingDirectory=localRepo)
    gitLog=str(results)
    for entry in gitLog.replace('\r','').split('\n\n'):
        yield GitCommit(entry)
