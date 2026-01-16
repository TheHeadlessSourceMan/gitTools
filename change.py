"""
Location of a single change.

This can represent a location in either
the before, or after file,
depending on self.differenceType. 
"""
import typing
from paths import FileLocation,UrlCompatible,Url,TextLocationSinglePoint
if typing.TYPE_CHECKING:
    from .difference import Difference


class ChangeLocationType:
    """
    Enum to determine whether this location
    is before the change, or after the change
    """
    FILE_BEFORE_CHANGE=0
    FILE_AFTER_CHANGE=1
    WITH_CONTEXT=2 # includes common context that has not changed
DifferenceLocationType=ChangeLocationType


class ChangeLocation(FileLocation):
    """
    Location of a single change.

    This can represent a location in either
    the before, or after file,
    depending on self.differenceType. 
    """
    def __init__(self,
        parent:'Difference',
        changeType:ChangeLocationType,
        line:int):
        """ """
        self.parent:'Difference'=parent
        self.lines:typing.List[str]=[]
        self.changeType=changeType
        FileLocation.__init__(self,fromRow=line)

    @property
    def url(self)->Url:
        """
        Url of this difference
        """
        url=self.parent.url.copy()
        # TODO: add line to url?
        return url
    @url.setter
    def url(self,url:UrlCompatible): # type: ignore
        _=url

    @property
    def toPoint(self)->TextLocationSinglePoint:
        """
        Calculates the to location point on-the-fly
        """
        return TextLocationSinglePoint(self.toRow,0)
    @toPoint.setter
    def toPoint(self,*args,**kwargs):
        _=args
        _=kwargs

    @property
    def toRow(self)->int:
        """
        ending row of this file location
        """
        if not self.lines:
            return self.fromRow
        return self.fromRow+len(self.lines)-1
    @toRow.setter
    def toRow(self,toRow:typing.Optional[int]=None):
        _=toRow

    @property
    def fromRow(self)->int:
        """
        ending row of this file location
        """
        return self.fromLine
    @fromRow.setter
    def fromRow(self,fromRow:typing.Optional[int]=None):
        _=fromRow

    @property
    def text(self)->str:
        """
        Text at this location
        """
        return '\n'.join(self.lines)
DifferenceLocation=ChangeLocation
