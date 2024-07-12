"""
Tools for managing git branches
"""
import typing
import os
from paths import UrlCompatible,asUrl
from k_runner.osrun import osrun
from gitTools.tagsAndVersions import (
    findRepoPath,GitCommit,Version,gitTagToCommit)


def gitAbandonChanges(localRepoPath:str)->None:
    """
    Shortcut to abandon all changes.

    WARNING: ability to shoot yourself in the foot is very high, here
    """
    cmd=['git','reset','--hard','HEAD']
    result=osrun(cmd,workingDirectory=localRepoPath)
    if result.stderr:
        raise Exception(result.stderr)
    cmd=['git','pull']
    _=osrun(cmd,workingDirectory=localRepoPath)


def revertCommits(commits:typing.Iterable[str],localRepoPath:str='.'):
    """
    revert a series of commits

    TODO: this is experimental/untested
    """
    repoPath=findRepoPath(localRepoPath)
    if repoPath is None:
        raise FileNotFoundError(f'"{localRepoPath}" is not a git repo')
    cmd=['git','revert','-n','']
    for commit in commits:
        cmd[-1]=commit
        print('$>',' '.join(cmd))
        result=osrun(cmd,workingDirectory=repoPath)
        if result.stderr:
            raise Exception(result.stderr)


def shutdownCodeDependentProcesses()->typing.List[str]:
    """
    Shut down all processes that are dependent on the current
    symlink/code so that new code can be checked out

    Returns list of processes that were shut down
    (so they could possibly be restarted when the new code
    is available)
    """
    ret:typing.List[str]=[]
    return ret


def restoreCodeDependentProcesses(
    originalRunningProcesses:typing.List[str]
    )->None:
    """
    TODO: restore all code dependent processes shut down by
        shutdownCodeDependentProcesses()
    """


def checkoutBranch(
    commitId:typing.Union[str,GitCommit,Version],
    localRepoPath:str=r"",
    symlinkLocation:str=r""
    )->None:
    """
    Check out a particular commit id.

    :commitId: can be a short or long hash, or a version number
    """
    import osTools.ln as ln
    if isinstance(commitId,Version):
        commitInfo=gitTagToCommit(localRepoPath,str(commitId))
        commitId=commitInfo.commitId
    elif isinstance(commitId,GitCommit):
        commitInfo=commitId
        commitId=commitInfo.commitId
    else:
        import re
        commitId=str(commitId)
        commitIdCheck=re.compile(r"""[0-9a-f]{7,128}""",re.IGNORECASE)
        if commitIdCheck.match(commitId) is None:
            # can't be a hash, must be a version
            tag=commitId
            commitInfo=gitTagToCommit(localRepoPath,commitId)
            commitId=commitInfo.commitId
            print(f'tag {tag} resolves to {commitId}')
    originalRunningProcesses:typing.Optional[typing.List[str]]=None
    def printerr(msg):
        print(msg)
    try:
        currentLocation=os.path.abspath(ln.linkTarget(symlinkLocation))
    except Exception:
        currentLocation='[[NOTHING]]'
    if currentLocation!=localRepoPath:
        print(f'need to change symlink from\n\t{currentLocation}\nto\n\t{localRepoPath}') # noqa: E501 # pylint: disable=line-too-long
        # start with a blank slate
        print('cleaning up existing ...')
        originalRunningProcesses=shutdownCodeDependentProcesses()
        print('removing link ...')
        ln.unlink(symlinkLocation)
        # select upstream as the current link
        print(f'updating link {symlinkLocation} to point to {localRepoPath} ...') # noqa: E501 # pylint: disable=line-too-long
        ln.ln(localRepoPath,symlinkLocation)
    # check out
    print(f'checking out {commitId} branch ...')
    cmd=['git','checkout',f'{commitId}']
    print('$>',' '.join(cmd))
    _=osrun(cmd,workingDirectory=localRepoPath,
        callOnStdoutLine=print,callOnStderrLine=printerr)
    if originalRunningProcesses is not None:
        restoreCodeDependentProcesses(originalRunningProcesses)
    print('done!')


def copyOverProjectDefaults(
    cwd:str,
    projDefaultsDir:typing.Optional[str]=None
    )->None:
    """
    Copy project default files over the top of any existing files.

    This is a crude, brute-force way to get a project configured
    the way you want it
    """
    import shutil
    print('copying over project defaults ...')
    if projDefaultsDir is None:
        projDefaultsDir=r"D:\python\data\editor_settings_defaults"
    print(f'  "{projDefaultsDir}/*" => "{cwd}"')
    try:
        shutil.copytree(projDefaultsDir,cwd)
    except FileExistsError:
        # if the defaults are already there, that's no bad thing
        pass


def createBranch(swr:str,
    gitProject='MyProject',
    gitLocation='d:\git'
    )->None:
    """
    note that the swr should be of the form:
        feature/SWR-12345
    or
        SWR-12345
    or a url whose end resource is an swr number
        https://mycompany-jira.atlassian.net/browse/SWR-136385

    WARNING: the steps here should be correct, but it has not been tested!

    NOTE: getting...
        "fatal: unable to access
        'https://something/something.git/':
        schannel: SNI or certificate check failed:
        SEC_E_WRONG_PRINCIPAL (0x80090322)
        - The target principal name is incorrect."
        usually means that the vpn is not logged in
    """
    from osTools import ln,unlink
    ANSI_RED="\033[0;31m"
    #ANSI_GREEN="\033[0;32m"
    ANSI_WHITE="\033[0;37m"
    def stdoutLine(s:str):
        print(f'{ANSI_WHITE}{s}')
    def stderrLine(s:str):
        print(f'{ANSI_RED}{s}{ANSI_WHITE}')
    originBranchUrl=f"https://github.com/user/{gitProject}.git"
    if swr.startswith('http'):
        # it's a url like https://mycompany-jira.atlassian.net/browse/SWR-123456
        swr=swr.rsplit('/',1)[-1].split('?',1)[0]
        tagSplit=[swr]
    else:
        # it's an swr or a tag/swr
        tagSplit=swr.rsplit('/',1)
    for i,tag in enumerate(tagSplit):
        if tag.lower().startswith(gitProject.lower()):
            tagSplit[i]=tag[len(gitProject):]
            while tag[0]=='_':
                tagSplit[i]=tag[1:]
    swr=tagSplit[-1].strip().upper()
    if len(tagSplit)<2:
        tag='feature'
    else:
        tag=tagSplit[0]
    taggedSwr=f'{tag}/{swr}'
    # start with a blank slate
    print('cleaning up existing ...')
    originalRunningProcesses=shutdownCodeDependentProcesses()
    cwd=gitLocation
    localRepoPath=f'{gitProject}_{swr}'
    localRepoPathAbsolute=f'{cwd}{os.sep}{localRepoPath}'
    projectSymlink=f'{gitProject}'
    projectSymlinkAbsolute=f'{cwd}{os.sep}{projectSymlink}'
    print('Using configuration:')
    print(f'\t{tag=}')
    print(f'\t{swr=}')
    print(f'\t{taggedSwr=}')
    print(f'\t{cwd=}')
    print(f'\t{localRepoPath=}')
    print(f'\t{localRepoPathAbsolute=}')
    print(f'\t{projectSymlink=}')
    print(f'\t{projectSymlinkAbsolute=}')
    print(f'removing {gitProject} link ...')
    unlink(os.sep.join((cwd,gitProject)))
    # git a clean copy of the source
    if os.path.isdir(localRepoPathAbsolute):
        print('directory already exists. not checking out')
    else:
        cmd=['git','clone',originBranchUrl,f'{localRepoPath}']
        print('&>',' '.join(cmd))
        result=osrun(cmd,workingDirectory=cwd,
            callOnStdoutLine=stdoutLine,callOnStderrLine=stderrLine)
        if result.stderr:# and not result.stderr.endswith(' done.'):
            print(result.stderr)
            #raise Exception(result.stderr)
    # select that as the current link
    linkLocation=os.sep.join((cwd,gitProject))
    linkTarget=os.sep.join((cwd,f'{gitProject}_{swr}'))
    print(f'updating link at {linkLocation} to point to {linkTarget} ...')
    ln(linkTarget,linkLocation)
    # create a new branch
    cwd=projectSymlinkAbsolute
    print(f'creating {taggedSwr} branch ...')
    cmd=['git','checkout','-b',taggedSwr]
    result=osrun(cmd,workingDirectory=cwd,
        callOnStdoutLine=stderrLine,callOnStderrLine=stderrLine)
    stderr=result.stderr.strip()
    if stderr and not stderr.startswith('Switched to'):
        if stderr.endswith(f"a branch named '{taggedSwr}' already exists"):
            print(f"a branch named '{taggedSwr}' already exists")
        else:
            raise Exception(result.stderr)
    cmd=['git','push','-u','origin',taggedSwr]
    result=osrun(cmd,workingDirectory=cwd,
        callOnStdoutLine=stderrLine,callOnStderrLine=stderrLine)
    stderr=result.stderr.strip()
    if stderr:
        if stderr.lower().find('err')>=0:
            raise Exception(stderr)
        print(stderr)
    print('') # because git omits the trailing newline
    copyOverProjectDefaults(cwd)
    restoreCodeDependentProcesses(originalRunningProcesses)
    print('done!')


def sanitizeBranchName(name:str)->str:
    """
    Attempts to make a branch name look like:
        feature/SWR-1234
            or
        fix/SWR-1234
    """
    a=name.split('/')
    if len(a)>2:
        raise Exception(f'Malformed "{name}"')
    a[-1]=a[-1].upper()
    if not a[-1].startswith('SWR-'):
        if a[-1].startswith('SWR'):
            a[-1]='SWR-'+a[-1][3:]
        else:
            a[-1]='SWR-'+a[-1]
    if len(a)==1:
        a.insert(0,'feature')
    return '/'.join(a)


def branchHyperlink(repoUrl:UrlCompatible,branchName:str)->str:
    """
    Get an <a href=> tag to a particular branch
    """
    return f'<a href="{asUrl(repoUrl)}/tree/{branchName}" target="_blank">{branchName}</a>' # noqa: E501 # pylint: disable=line-too-long
