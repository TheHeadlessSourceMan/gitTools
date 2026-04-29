"""
Wrapper for a git repo
"""
import typing
from stringTools.versions import Version
from paths import (
    UrlCompatible,URL,FileUrlCompatible,FileUrl)
from gitTools.branches import gitAbandonChanges
from gitTools.commits import (
    findRepoInfo,gitLog,gitCommitsForFunction,gitCommitsForLine)
from gitTools.gitCommits import GitCommits
from pullRequests import getPRs
from tagsAndVersions import gitLatestReleaseVersion,gitTags,gitVersionTags
from gitRemotes import addGitRemote, listGitRemotes,GitRemote,githubUrl
from .diff import MultifileDiff
from .exceptions import GitException


class GitRepo:
    """
    Wrapper for a git repo
    """

    MASTER_BRANCH_NAME='origin/master'
    UPSTREAM_BRANCH_NAME='upstream'

    def __init__(self,
        localRepoPath:FileUrlCompatible='.',
        url:typing.Optional[UrlCompatible]=None):
        """ """
        if url is None:
            url=githubUrl(localRepoPath)
            if url is None:
                raise FileNotFoundError(f'Location "{localRepoPath}" is not a git project') # noqa: E501 # pylint: disable=line-too-long
            self.githubUrl:URL=url
        else:
            self.githubUrl=URL(url)
        self._localRepoPath=FileUrl(localRepoPath,shellReplace=True).absolute()
        self.info=findRepoInfo(self._localRepoPath)
        if self.info is None:
            msg=f'"{self._localRepoPath}" is not a valid git repository!'
            raise FileNotFoundError(msg)
        self._remotes:typing.Optional[
            typing.List[GitRemote]]=None

    @property
    def localRepoPath(self)->FileUrl:
        """
        Get the local path to the repo
        """
        return self._localRepoPath
    @property
    def repoPath(self)->FileUrl:
        """
        Get the local path to the repo
        """
        return self._localRepoPath

    def goToGithub(self,additional="")->None:
        """
        Open github for this repo in a browser
        """
        if self.githubUrl is None:
            raise Exception("Unable to determine github url for repo")
        if additional:
            (self.githubUrl+additional).openInBrowser()
        else:
            self.githubUrl.openInBrowser()

    @property
    def githubUserName(self)->str:
        """
        Return the local github user name
        """
        return self.info['githubUser']

    @property
    def githubProjectName(self)->str:
        """
        Return the github project name for the current direcotry
        """
        return self.info['githubProject']

    @property
    def githubRepoName(self)->str:
        """
        Return the github repo name for the current direcotry
        """
        return self.githubUserName+self.githubProjectName
    @property
    def name(self):
        """
        Return the github repo name for the current direcotry
        """
        return self.githubRepoName

    def goToGithubPullRequests(self)->None:
        """
        List active pull requests
        """
        self.goToGithub('pulls')

    def goToGithubIssues(self)->None:
        """
        List active pull issues
        """
        self.goToGithub('issues')

    def goToGithubCommit(self,commitId:str)->None:
        """
        Checkout a particular commit
        """
        self.goToGithub(f'commits/{commitId}')

    def goToGithubBranch(self,branchName:str)->None:
        """
        Check out a particular branch
        """
        self.goToGithub(f'tree/{branchName}')

    def goToGithubBranchCompare(self,branchName1:str,branchName2:str)->None:
        """
        View the online compare between two branch/commits
        """
        self.goToGithub(f'compare/{branchName1}...{branchName2}')

    def goToGithubFile(self,commitId:str,repoFilePath:str,line:int=0)->None:
        """
        View the online file of a particaular commit
        """
        s=f'blob/{commitId}/{repoFilePath}'
        if line>0:
            s=f'{s}#L{line}'
        self.goToGithub(s)

    def goToGithubFileHistory(self,commitId:str,repoFilePath:str)->None:
        """
        View the online file of a particaular commit
        """
        self.goToGithub(f'commits/{commitId}/{repoFilePath}')

    def goToGithubRelease(self,tag:str)->None:
        """
        View a release online
        """
        self.goToGithub(f'releases/tag/{tag}')

    @property
    def remotes(self)->typing.Iterable[GitRemote]:
        """
        List all known remotes of this repo
        """
        if self._remotes is None:
            self._remotes=list(listGitRemotes(self.localRepoPath))
        return self._remotes # type: ignore

    @property
    def upstream(self)->typing.Optional[GitRemote]:
        """
        Get/set the upstream remote
        """
        for remote in self.remotes:
            if remote.name=='upstream':
                return remote
        return None
    @upstream.setter
    def upstream(self,upstream:typing.Union[UrlCompatible,GitRemote]):
        if isinstance(upstream,GitRemote):
            upstream=upstream.url

    def addGitRemote(self,name:str,url:UrlCompatible):
        """
        Add a new git remote
        """
        addGitRemote(self.localRepoPath,name,url)
        self._remotes=None # must be reloaded
    addRemote=addGitRemote

    def gitLog(self,moreparams="")->GitCommits:
        """
        get the history log
        """
        return gitLog(self.localRepoPath,moreparams)
    history=gitLog

    @property
    def allCommits(self)->GitCommits:
        """
        Return a list of all connits for this project
        """
        return self.gitLog()

    @property
    def differencesFromMaster(self):
        """
        Return all commits of the current branch
        that are not yet in master.
        """
        return self.differencesFromBranch(self.MASTER_BRANCH_NAME)

    @property
    def differencesFromUpstream(self):
        """
        Return all commits of the current branch
        that are not yet in the upstream fork.
        """
        return self.differencesFromBranch(self.UPSTREAM_BRANCH_NAME)

    def differencesFromBranch(self,
        branchName:str
        )->MultifileDiff:
        """
        Return all commits of the current branch
        that are not in a selected branch.

        To get these sorted by file, you can use getFileDiffs().
        """
        #from k_runner import osrun
        import subprocess
        cmd=['git','diff',branchName]
        #result=osrun(cmd,workingDirectory=self.localRepoPath,shell=True)
        out,_=subprocess.Popen(cmd,shell=True,cwd=str(self.localRepoPath),
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT).communicate()
        result=out.decode('utf-8',errors='ignore')
        if result.find('\nfatal: '):
            # I'm no doctor, but...
            # anything fatal is not good for your health
            if branchName==self.UPSTREAM_BRANCH_NAME\
                and result.find("fatal: 'upstream' does not appear to be a git repository")>=0:
                msg="""upstream repositry is not set.  Either:
                    a) in python gitRepo.upstream="https://girhub.com/REPO_MAINTAINER/REPO.git"
                    b) or run:
                        git remote add upstream https://github.com/REPO_MAINTAINER/REPO.git
                        git fetch upstream
                    """
                raise GitException(msg)
            raise GitException(result)
        return MultifileDiff(result)

    def commitsForLine(self,
        repoFilename:FileUrlCompatible,
        startLine:int,
        endLine:typing.Optional[int]=None,
        offset:int=0
        )->GitCommits:
        """
        Get all commits that affect a particular line
        """
        return gitCommitsForLine(
            self.localRepoPath,repoFilename,startLine,endLine,offset)
    gitCommitsForLine=commitsForLine

    def commitsForFunction(self,
        repoFilename:FileUrlCompatible,functionName:str
        )->GitCommits:
        """
        Get all commits that affect a particular function
        """
        return gitCommitsForFunction(
            self.localRepoPath,repoFilename,functionName)
    gitCommitsForFunction=commitsForFunction

    def getPRs(self,
        author:typing.Optional[str]=None,
        limit:int=30,
        state:str='open',
        baseBranch:typing.Optional[str]=None):
        """
        Get all pull requests
        """
        return getPRs(self.localRepoPath,author,limit,state,baseBranch)
    @property
    def openPRs(self):
        """
        Get all open pull requests
        """
        return self.getPRs

    def gitAbandonChanges(self)->None:
        """
        Abandon all current changes
        """
        gitAbandonChanges(self.localRepoPath)
    abandonChanges=gitAbandonChanges

    def gitTags(self)->typing.List[str]:
        """
        List all git tags
        """
        return gitTags(self.localRepoPath)
    @property
    def tags(self)->typing.List[Version]:
        """
        List all git tags
        """
        return self.gitVersionTags()

    def gitVersionTags(self)->typing.List[Version]:
        """
        List all git version number tags
        """
        return gitVersionTags(self.localRepoPath)
    @property
    def versions(self)->typing.List[Version]:
        """
        List all git version number tags
        """
        return self.gitVersionTags()

    def gitLatestReleaseVersion(self)->Version:
        """
        List the latest released version
        """
        return gitLatestReleaseVersion(self.localRepoPath)
    @property
    def currentVersion(self)->Version:
        """
        Get the current version
        """
        return self.gitLatestReleaseVersion()
    @property
    def latestVersion(self)->Version:
        """
        Get the current version
        """
        return self.gitLatestReleaseVersion()

    @property
    def nextVersion(self)->Version:
        """
        Get the next version
        """
        n=str(self.currentVersion).split('.')
        n[2]=str(int(n[2])+1)
        return Version('.'.join(n))
    @property
    def nextRelease(self)->Version:
        """
        Get the next version
        """
        return self.nextVersion
