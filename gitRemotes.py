"""
Manage remotes for a repo
"""
import typing
from paths import (
    URL,FilePathCompatible,UrlCompatible,asFilePath,asUrl)
from k_runner.osrun import osrun
from gitTools.exceptions import GitException


class GitRemote:
    """
    A git remote location
    """
    def __init__(self,name:str,url:UrlCompatible,extra:str):
        self.name=name
        self.url=URL(url)
        self.extra=extra


def listGitRemotes(
    localRepoPath:FilePathCompatible
    )->typing.Iterable[GitRemote]:
    """
    List all remotes for a local repo
    """
    ret=[]
    cmd=['git','remote','-v']
    result=osrun(cmd,workingDirectory=asFilePath(localRepoPath))
    for line in result:
        abc=line.split()
        if len(abc)==3:
            ret.append(GitRemote(
                abc[0],
                abc[1],
                abc[2].replace('(','').replace(')','')
                ))
    return ret


def addGitRemote(
    localRepoPath:FilePathCompatible,
    name:str,
    url:UrlCompatible):
    """
    Add a new git remote
    """
    cmd=['git','remote','add',name,str(asUrl(url))]
    result=osrun(cmd,workingDirectory=asFilePath(localRepoPath))
    out=result.stdOutErr
    if out.find('\nfatal: ')>=0:
        raise GitException(out)


def githubRemote(
    localRepoPath:FilePathCompatible
    )->typing.Optional[GitRemote]:
    """
    Get the github remote for a local repo
    """
    for remote in listGitRemotes(asFilePath(localRepoPath)):
        if str(remote.url).find('github')>=0:
            return remote
    return None


def githubUrl(
    localRepoPath:FilePathCompatible
    )->typing.Optional[URL]:
    """
    Get the github url for a local repo

    This is technically not part of the 'git remote' command
    but it seems like it would be, so people will probably
    look here to find it.
    """
    cmd=['git','config','--get-regexp','remote.origin.url.*']
    result=osrun(cmd,workingDirectory=asFilePath(localRepoPath))
    resultArray=str(result).strip().split(' ',1)
    if len(resultArray)>1:
        result=resultArray[1].rsplit('.git',1)[0]
        return URL(result)
    return None
