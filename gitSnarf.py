"""
Tool for searching for which git checkin
introduced a particular issue.
"""
import typing
import datetime
from gitTools.gitCommit import GitCommit
from gitTools.gitCommits import GitCommits
from gitTools.commits import gitLog


class GitSnarf:
    """
    Tool for searching for which git checkin
    introduced a particular issue.

    TODO: there is some overlap between this and GitCommits.findDefect()
    """

    def __init__(self,
        testFn:typing.Callable[[],bool],
        localRepoPath:str=r""):
        """ """
        self.testFn:typing.Callable[[],bool]=testFn
        self.localRepoPath=localRepoPath
        self._gitCommits:GitCommits=GitCommits()

    @property
    def gitCommits(self)->GitCommits:
        """
        The history of git versions
        """
        if self._gitCommits is None:
            self._gitCommits=gitLog(self.localRepoPath)
        return self._gitCommits

    def _binSearch(self,
        dataset:typing.List[typing.Any],
        testFn:typing.Callable[[typing.Any],bool]
        )->int:
        """
        Given an ordered list and a function that takes a value
        and returns true/false
        determines at what point in that list the function changes
        from True to False

        Eg [True,True,True,False,False]=>3
        """
        tested:typing.List[typing.Optional[bool]]=[None for _ in dataset]
        # initial sanity checking
        tested[0]=testFn(dataset[0])
        if not tested[0]:
            raise Exception('Not even the first commit passed the test!')
        tested[-1]=testFn(dataset[-1])
        if tested[-1]:
            raise Exception('Not even the last commit failed the test!')
        if len(dataset)<=2:
            return 0
        # perform the search
        start=0
        end=len(dataset)-1
        while start <= end:
            mid=(start+end)//2
            tested[mid]=testFn(dataset[mid])
            if tested[mid-1] and not tested[mid]:
                return mid
        return len(dataset)-1

    def _findVersionIdx(self,
        findVersion:typing.Union[None,str,GitCommit,datetime.datetime]=None,
        )->int:
        """
        find the index of a particular checkin version

        TODO: need to check short version hashes as well!
        """
        if findVersion is None:
            raise Exception('Searching for None')
        if not isinstance(findVersion,datetime.datetime):
            if isinstance(findVersion,GitCommit):
                findVersion=findVersion.commitId
            for i,commit in enumerate(self.gitCommits):
                if commit.commitId==findVersion:
                    return i
            raise Exception(f'Could not find version {findVersion}')
        # search by what code was in-effect at date
        best=0
        for i,commit in enumerate(self.gitCommits):
            if commit.date is not None and commit.date>findVersion:
                return best
            best=i
        return best

    def findVersion(self,
        findVersion:typing.Union[None,str,GitCommit,datetime.datetime]=None,
        )->GitCommit:
        """
        Find a particular checkin by date or by hash.
        """
        return self.gitCommits[self._findVersionIdx(findVersion)]

    def whichVersionBroke(self,
        startVersion:typing.Union[None,str,datetime.datetime]=None,
        endVersion:typing.Union[None,str,datetime.datetime]=None
        )->GitCommit:
        """
        find out what version caused a bug by way of running a
        testFn (binary search pattern)

        :startVersion: can be a datetime to start at, a version hash,
            or None to start at the beginning of time
        :endVersion: can be a datetime to end at, a version hash,
            or None to end at the most current version
        """
        from branches import checkoutBranch
        if startVersion is None:
            startVersionIdx=0
        else:
            startVersionIdx=self._findVersionIdx(startVersion)
        if endVersion is None:
            endVersionIdx=len(self.gitCommits)-1
        else:
            endVersionIdx=self._findVersionIdx(endVersion)
        def runTest(ci:GitCommit)->bool:
            print(f'testing commit: {ci.commitId}')
            checkoutBranch(ci.commitId)
            return self.testFn()
        idx=self._binSearch(
            self.gitCommits[startVersionIdx:endVersionIdx],runTest)
        return self.gitCommits[idx]
