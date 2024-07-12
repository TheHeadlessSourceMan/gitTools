"""
Tools for working with git tags and versions
"""
import typing
from paths import URL
from k_runner.osrun import osrun
from stringTools.versions import Version, VersionCompatible, asVersion
from gitTools.gitCommit import GitCommit
from gitTools.commits import findRepoPath, gitLog, findRepoInfo


def gitTags(localRepoPath:str='.')->typing.List[str]:
    """
    List all the tags associated with a git repo
    """
    repoPath=findRepoPath(localRepoPath)
    cmd=['git','tag']
    result=osrun(cmd,workingDirectory=repoPath)
    return result.stdouterr.split('\n')


def gitVersionTags(localRepoPath:str='.')->typing.List[Version]:
    """
    Similar to gitTags, but drops everything that doesn't look like a version
    and returns a list of version structs in descending order
    ( gitVersions()[0] is latest version )
    """
    ret:typing.List[Version]=[]
    for tag in gitTags(localRepoPath):
        tag=tag.strip()
        if tag and tag[0].isdigit() and tag.find('.')>0:
            # call it a version
            ver=Version(tag)
            ret.append(ver)
    ret.sort(reverse=True)
    return ret


def gitLatestReleaseVersion(localRepoPath:str='.')->Version:
    """
    takes the version tags from gitVersionTags() and returns
    the first one that is a release version
    """
    versions=gitVersionTags(localRepoPath)
    for version in versions:
        if version.release:
            return version
    return versions[-1]


def tagUrl(tag:str,localRepoPath:str='.'):
    """
    Get a url to jump to view a tag on github
    """
    info=findRepoInfo(localRepoPath)
    githubUrl=info['githubUrl']
    return URL(f'{githubUrl}/releases/tag/{tag}')


def gitTagToCommit(tag:str,localRepoPath:str='.')->GitCommit:
    """
    Get the latest checkout commit id for a particular tag
    """
    return gitLog(localRepoPath,moreparams=tag)[0]


def viewChangesBetweenVersions(
    fromVersion:VersionCompatible,
    toVersion:VersionCompatible,
    localRepoPath:str='.'
    )->None:
    """
    Open a url capable of listing all changes between two release versions

    NOTE: to simply get that url, use changesBetweenVersionsUrl()
    """
    url=changesBetweenVersionsUrl(fromVersion,toVersion,localRepoPath)
    url.openInBrowser()


def changesBetweenVersionsUrl(
    fromVersion:VersionCompatible,
    toVersion:VersionCompatible,
    localRepoPath:str='.'
    )->URL:
    """
    Get a url capable of listing all changes between two release versions
    """
    info=findRepoInfo(localRepoPath)
    githubUrl=info['githubUrl']
    # NOTE: can use +'0.0.0.0' to ensure the right number of digits
    fromVersion=asVersion(fromVersion)+'0.0.0.0'
    toVersion=asVersion(toVersion)+'0.0.0.0'
    return URL(f'{githubUrl}/compare/{fromVersion}...{toVersion}')


def getCurrentWorkingRelease(
    localRepoPath:str,
    versionAdd:VersionCompatible="0.0.1.0"
    )->Version:
    """
    Get the current working release number.
    This is calculated as the last release, plus a versionAdd amount.
    """
    return gitLatestReleaseVersion(localRepoPath)+versionAdd
