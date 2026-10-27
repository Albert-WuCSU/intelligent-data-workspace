"""Windows handle pinning for fixed runtime objects; no path-based recursive delete."""
from contextlib import ExitStack
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
from .retention import MAX_FILE_BYTES
from .upload_preflight import checked_runtime_path


class PinnedObject:
    def __init__(self, root, path, *, directory=False, delete=False, mutable=False):
        if os.name != 'nt': raise OSError('native pinning unavailable')
        import win32file, win32con
        self.api=win32file; self.handle=None; self.directory=directory
        self.path=checked_runtime_path(root,path)
        flags=0x00200000 | win32con.FILE_FLAG_BACKUP_SEMANTICS
        access=win32con.GENERIC_READ | (win32con.DELETE if delete else 0)
        sharing=win32con.FILE_SHARE_READ | (win32con.FILE_SHARE_WRITE if directory or mutable else 0)
        try:
            self.handle=win32file.CreateFile(str(self.path),access,sharing,None,win32con.OPEN_EXISTING,flags,None)
            info=win32file.GetFileInformationByHandle(self.handle)
            if info[0] & 0x00000400: raise OSError('reparse object')
            if bool(info[0] & win32con.FILE_ATTRIBUTE_DIRECTORY) != directory: raise OSError('object type changed')
            if not directory and info[7] != 1: raise OSError('hardlinked file')
            final=win32file.GetFinalPathNameByHandle(self.handle,0)
            prefix=chr(92)*2+'?'+chr(92)
            if final.startswith(prefix):final=final[4:]
            if Path(final) != self.path: raise OSError('native path mismatch')
            self.identity={'volume':info[4],'index':(info[8]<<32)|info[9]}
            self.size=(info[5]<<32)|info[6]
        except BaseException:
            self.close();raise

    def read(self,limit=MAX_FILE_BYTES):
        self.api.SetFilePointer(self.handle,0,0)
        chunks=[];total=0
        while True:
            _,chunk=self.api.ReadFile(self.handle,min(65536,limit+1-total))
            if not chunk:break
            total+=len(chunk)
            if total>limit:raise ValueError('pinned read budget')
            chunks.append(chunk)
        return b''.join(chunks)

    def record(self):
        if self.size>MAX_FILE_BYTES:raise ValueError('pinned file budget')
        content=self.read()
        if len(content)!=self.size:raise ValueError('native file size changed')
        return {**self.identity,'size':self.size,'sha256':hashlib.sha256(content).hexdigest()}

    def dispose(self):
        # Delete the validated object through THIS handle, never resolve the pathname again.
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        method=kernel.SetFileInformationByHandle
        method.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
        method.restype=wintypes.BOOL
        flag=wintypes.BOOL(True)
        if not method(int(self.handle),4,ctypes.byref(flag),ctypes.sizeof(flag)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.close()

    def close(self):
        if self.handle is not None:self.handle.Close();self.handle=None

    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def pin_directories(stack,root,folder,*,delete_folder=True):
    # Pin every ancestor so none of the checked absolute targets can be moved/replaced.
    root=Path(root);folder=checked_runtime_path(root,folder)
    chain=list(reversed(folder.parents))+[folder]
    for path in chain:
        # Ancestors outside runtime are opened read-only solely to prevent path replacement.
        checked_runtime_path(path,path)
        obj=stack.enter_context(PinnedObject(path,path,directory=True,delete=delete_folder and path==folder))
        if path==folder:return obj
