"""
A set of differences for a git file
"""
import typing
import datetime
from paths import Url
from codeTools import FileDifferences,MultiFileDifferences
if typing.TYPE_CHECKING:
    from gitTools.gitCommit import GitCommit


class GitDifferences(FileDifferences):
    """
    A set of differences for a git file
    """
    def __init__(self,
        data:str,
        commit:typing.Optional["GitCommit"]=None):
        """ """
        self.commit=commit
        super().__init__(data)

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


class GitMultiDifferences(MultiFileDifferences):
    """
    A git diff containing multiple files
    """

    def __init__(self,
        data:str='',
        date:typing.Optional[datetime.datetime]=None,
        commit:typing.Optional["GitCommit"]=None):
        """
        """
        self.commit=commit
        MultiFileDifferences.__init__(self,data,date)

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
            fd=GitDifferences("diff --git "+f,commit=self.commit)
            setattr(fd,"date",self.date)
            self.fileDiffs[fd.filename]=fd
