import ctypes
from time import sleep
from dataclasses import dataclass, InitVar
from dxcam._libs.d3d11 import *
from dxcam._libs.dxgi import *
from dxcam.core.device import Device
from dxcam.core.output import Output

#class ac_Cursor:
#    _fields_ = [("PointerPositionInfo",DXGI_OUTDUPL_POINTER_POSITION), ("PointerShapeInfo", DXGI_OUTDUPL_POINTER_SHAPE_INFO), ("Shape", bytes)]


@dataclass
class Duplicator:
    texture: ctypes.POINTER(ID3D11Texture2D) = ctypes.POINTER(ID3D11Texture2D)()
    duplicator: ctypes.POINTER(IDXGIOutputDuplication) = None
    updated: bool = False
    output: InitVar[Output] = None
    device: InitVar[Device] = None
    #cursor: ctypes.POINTER(ID3D11Texture2D) = ctypes.POINTER(ID3D11Texture2D)() #use proper type
    cursor = ac_Cursor()
    cursor.shape: bytes = None
    cursor.PointerShapeInfo: DXGI_OUTDUPL_POINTER_SHAPE_INFO = DXGI_OUTDUPL_POINTER_SHAPE_INFO()  

    def __post_init__(self, output: Output, device: Device) -> None:
        self.duplicator = ctypes.POINTER(IDXGIOutputDuplication)()
        output.output.DuplicateOutput(device.device, ctypes.byref(self.duplicator))

    def update_frame(self):
        info = DXGI_OUTDUPL_FRAME_INFO()
        res = ctypes.POINTER(IDXGIResource)()
        try:
            self.duplicator.AcquireNextFrame(
                1000,
                ctypes.byref(info),
                ctypes.byref(res),
            )
        except comtypes.COMError as ce:
            if ctypes.c_int32(DXGI_ERROR_ACCESS_LOST).value == ce.args[0] or ctypes.c_int32(ABANDONED_MUTEX_EXCEPTION).value == ce.args[0]:
                self.release()  # Release resources before reinitializing
                sleep(0.1)
                self.__post_init__(self.output, self.device)
                return False
            if ctypes.c_int32(DXGI_ERROR_WAIT_TIMEOUT).value == ce.args[0]:
                self.updated = False
                return True
            else:
                raise ce
        try:
            self.texture = res.QueryInterface(ID3D11Texture2D)
        except comtypes.COMError as ce:
            self.duplicator.ReleaseFrame()
        try:
            new_PointerInfo, new_PointerShape = self.get_frame_pointer_shape(info)
            if new_PointerShape != False:
                self.cursor.Shape = new_PointerShape
                self.cursor.PointerShapeInfo = new_PointerInfo
                self.cursor.PointerPositionInfo = info.PointerPosition
        except Exception as e: 
            print(e)
        self.updated = True
        return True

    def release_frame(self):
        self.duplicator.ReleaseFrame()

    def release(self):
        if self.duplicator is not None:
            self.duplicator.Release()
            self.duplicator = None

    def get_frame_pointer_shape(self, FrameInfo):
        PointerShapeInfo = DXGI_OUTDUPL_POINTER_SHAPE_INFO()  
        buffer_size_required = ctypes.c_uint()
        pPointerShapeBuffer  = (ctypes.c_byte*FrameInfo.PointerShapeBufferSize)()
        #try:
            # Get shape
        hr = self.duplicator.GetFramePointerShape(FrameInfo.PointerShapeBufferSize, ctypes.byref(pPointerShapeBuffer), ctypes.byref(buffer_size_required), ctypes.byref(PointerShapeInfo)) 
        if FrameInfo.PointerShapeBufferSize > 0:
            print("T",PointerShapeInfo.Type,PointerShapeInfo.Width,"x",PointerShapeInfo.Height,"Pitch:",PointerShapeInfo.Pitch,"HS:",PointerShapeInfo.HotSpot.x,PointerShapeInfo.HotSpot.y)
            if PointerShapeInfo.Type != 2: return False # cant handle others rn
            return PointerShapeInfo, pPointerShapeBuffer
        #except:
        #    return False
        #return False
        return False

    def __repr__(self) -> str:
        return "<{} Initalized:{}>".format(
            self.__class__.__name__,
            self.duplicator is not None,
        )
