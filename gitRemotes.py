"""
Manage remotes for a repo
"""
import typing
from paths import URL
from k_runner import osrun


def listGitRemotes(
    localRepoPath:str
    )->typing.Iterable[typing.Tuple[str,URL,str]]:
    """
    List all remotes for a local repo
    """
    ret=[]
    cmd=['git','remote','-v']
    result=osrun.osrun(cmd,workingDirectory=localRepoPath)
    for line in result:
        abc=line.split()
        if len(abc)==3:
            ret.append((
                abc[0],
                URL(abc[1]),
                abc[2].replace('(','').replace(')','')
                ))
    return ret

def githubRemote(localRepoPath:str)->typing.Optional[URL]:
    """
    Get the github remote for a local repo
    """
    for _,remote,_ in listGitRemotes(localRepoPath):
        if str(remote).find('github')>=0:
            return remote
    return None

def githubUrl(localRepoPath:str)->typing.Optional[URL]:
    """
    Get the github url for a local repo

    This is technically not part of the 'git remote' command
    but it seems like it would be, so people will probably
    look here to find it.
    """
    cmd=['git','config','--get-regexp','remote.origin.url.*']
    result=osrun.osrun(cmd,workingDirectory=localRepoPath)
    result=str(result).strip().split(' ',1)
    if len(result)>1:
        return result[1].rsplit('.git',1)[0]
    return None
