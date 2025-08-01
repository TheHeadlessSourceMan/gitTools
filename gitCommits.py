"""
A series of git commits
(can be parsed from, git log output)

NOTE: always in chronological order, newst->oldest
"""
import typing
import datetime
try:
    import regex as re # type: ignore
except ImportError:
    import re
from gitRemotes import githubUrl
from gitTools.gitCommit import GitCommit


GitCommitsCompatible=typing.Union[
    GitCommit,
    "GitCommits",
    typing.Iterable["GitCommitsCompatible"]]


class GitCommits:
    """
    A series of git commits
    (can be parsed from, git log output)

    NOTE: always in chronological order, newst->oldest
    """

    def __init__(self,
        commits:typing.Optional[GitCommitsCompatible]=None,
        gitLogOutput:typing.Union[None,str,typing.List[str]]=None,
        repoPath:typing.Optional[str]=None
        ):
        """ """
        self.repoPath=repoPath
        self._githubRemote:typing.Optional[str]=None
        self._commits:typing.List[GitCommit]=[]
        if gitLogOutput is not None:
            self.parseGitLogOutput(gitLogOutput)
        if commits is not None:
            self.append(commits)

    @property
    def githubUrl(self)->typing.Optional[str]:
        """
        The remote github url for this commit
        """
        if self._githubRemote is None:
            if self.repoPath is not None:
                self._githubRemote=githubUrl(self.repoPath) # type: ignore
        return self._githubRemote

    def __len__(self)->int:
        return len(self._commits)
    @typing.overload
    def __getitem__(self,idx:slice)->typing.Iterable[GitCommit]:
        ...
    @typing.overload
    def __getitem__(self,idx:int)->GitCommit:
        ...
    def __getitem__(self,
        idx:typing.Union[int,slice]
        )->typing.Union[GitCommit,typing.Iterable[GitCommit]]:
        return self._commits[idx]
    def __iter__(self)->typing.Iterator[GitCommit]:
        return iter(self._commits)
    def append(self,commits:GitCommitsCompatible)->None:
        """
        Add new commit(s) to the list
        """
        if isinstance(commits,GitCommit):
            for i,commit in enumerate(self._commits):
                if commit>commits:
                    self._commits.insert(i,commits)
                    return
                elif commit.hash==commits.hash: #already in the list
                    return
            self._commits.append(commits)
        else:
            for commit in commits:  # type:ignore
                self.append(commit)
    add=append
    extend=append

    def clone(self)->"GitCommits":
        """
        Create a copy of this object
        """
        return GitCommits(self)
    copy=clone

    def union(self,commits:GitCommitsCompatible)->"GitCommits":
        """
        Combine two set of commits
        """
        return GitCommits([self,commits])

    def clear(self)->None:
        """
        Reset this object
        """
        self._commits=[]

    def assign(self,commits:GitCommitsCompatible)->None:
        """
        Reassign the value of this object
        """
        self.clear()
        self.append(commits)

    def between(self,
        startDate:datetime.datetime,
        endDate:datetime.datetime
        )->"GitCommits":
        """
        Get commits between two dates
        """
        gc=GitCommits()
        for commit in self._commits:
            if commit>startDate and commit<endDate:
                gc.append(commit)
        return gc
    def before(self,endDate:datetime.datetime)->"GitCommits":
        """
        Get commits before a certain date
        """
        gc=GitCommits()
        for commit in self._commits:
            if commit<endDate:
                gc.append(commit)
        return gc
    def after(self,startDate:datetime.datetime)->"GitCommits":
        """
        Get commits after a certain date
        """
        gc=GitCommits()
        for commit in self._commits:
            if commit>startDate:
                gc.append(commit)
        return gc
    since=after

    def findDefect(self,testFn:typing.Callable[[GitCommit],bool]
        )->typing.Optional[GitCommit]:
        """
        find which GitCommit introduces a defect by running
        a user-defined test for said defect

        Generally testFn will:
            1) checkout the commit given
            2) clean build it
            3) run a test to determine whether the defect is present or not
            4) return True/Fase whether it passed

        TIP: this can be leveraged for other searches as well,
            for instace findWhenAdded() uses
            it to perfom a regex search on code changes
        """
        count=len(self)
        hasDefect:typing.List[typing.Optional[bool]]=[None]*count
        def test(idx:int)->bool:
            if hasDefect[idx] is None:
                hasDefect[idx]=testFn(self._commits[idx])
            return hasDefect[idx] # type: ignore
        def bracketSearch(startIdx:int,endIdx:int)->typing.Optional[GitCommit]:
            if startIdx==endIdx:
                if test(startIdx):
                    return None
                return self._commits[startIdx]
            middleIdx=startIdx+((startIdx+endIdx)//2)
            ret=bracketSearch(startIdx,middleIdx)
            if ret is not None:
                return ret
            return bracketSearch(middleIdx,endIdx)
        return bracketSearch(0,count-1)

    def findWhenAdded(self,
        findRe:typing.Union[str,typing.Pattern]
        )->typing.Optional[GitCommit]:
        """
        find the commit when matching regex was added
        """
        if isinstance(findRe,str):
            findRe=re.compile(findRe,re.DOTALL)
        def test(commit:GitCommit)->bool:
            inOld=findRe.search(commit.oldCode) # type:ignore
            inNew=findRe.search(commit.newCode) # type:ignore
            return (inOld is None) and (inNew is not None)
        return self.findDefect(test)

    def findWhenRemoved(self,
        findRe:typing.Union[str,typing.Pattern]
        )->typing.Optional[GitCommit]:
        """
        find the commit when matching regex was removed
        """
        if isinstance(findRe,str):
            findRe=re.compile(findRe,re.DOTALL)
        def test(commit:GitCommit)->bool:
            inOld=findRe.search(commit.oldCode) # type:ignore
            inNew=findRe.search(commit.newCode) # type:ignore
            return (inOld is not None) and (inNew is None)
        return self.findDefect(test)

    def parseGitLogOutput(self,
        gitLogOutput:typing.Union[str,typing.Iterable[str]]
        )->None:
        """
        Parse the output from a "git log" command line command
        """
        if isinstance(gitLogOutput,str):
            gitLogOutput=gitLogOutput.split('\n')
        self._commits=[]
        descriptionLines:typing.List[str]=[]
        currentCommit=None
        for line in gitLogOutput:
            if len(line)==47 and line.startswith('commit '):
                # starting new commit
                if currentCommit is not None:
                    self._commits.append(currentCommit)
                currentCommit=GitCommit(
                    line[7:],githubUrl=self.githubUrl)
            elif currentCommit is not None:
                if currentCommit._gatheringLines: # noqa: E501 # pylint: disable=W0212
                    currentCommit._lines.append(line) # noqa: E501 # pylint: disable=W0212
                elif currentCommit._gatheringDescription: # noqa: E501 # pylint: disable=W0212
                    if line and line[0] not in (' ','\t'):
                        # switch to gathering code
                        currentCommit._gatheringDescription=False # noqa: E501 # pylint: disable=W0212
                        currentCommit._gatheringLines=True # noqa: E501 # pylint: disable=W0212
                        currentCommit.description= \
                            '\n'.join(descriptionLines).strip()
                    else:
                        descriptionLines.append(line.strip())
                elif not line.strip():
                    # switch to gathering description
                    currentCommit._gatheringDescription=True # noqa: E501 # pylint: disable=W0212
                    descriptionLines=[]
                elif line.startswith('Date:'):
                    currentCommit.date=' '.join(line.split()[1:])
                elif line.startswith('Author:'):
                    currentCommit.author=' '.join(line.split()[1:])
        if currentCommit is not None:
            self._commits.append(currentCommit)

    def __repr__(self)->str:
        return '\n'.join(repr(c) for c in self._commits)
