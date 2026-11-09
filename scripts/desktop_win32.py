"""Native Unicode window using ctypes; Python builds without Tk are supported."""
import ctypes
from ctypes import wintypes as W

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)


class NativeWindow:
    def __init__(self, owner):
        self.owner = owner
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.user.DefWindowProcW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
        self.user.DefWindowProcW.restype = LRESULT
        self.user.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD,
                                             ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                             W.HWND, W.HMENU, W.HINSTANCE, ctypes.c_void_p]
        self.user.CreateWindowExW.restype = W.HWND
        self.user.SetWindowTextW.argtypes = [W.HWND, W.LPCWSTR]
        self.user.EnableWindow.argtypes = [W.HWND, W.BOOL]
        self.user.DestroyWindow.argtypes = [W.HWND]
        self.user.ShowWindow.argtypes = [W.HWND, ctypes.c_int]
        self.user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
        self.user.SendMessageW.restype = LRESULT
        self.user.MessageBoxW.argtypes = [W.HWND, W.LPCWSTR, W.LPCWSTR, W.UINT]
        self.user.SetTimer.argtypes = [W.HWND, ctypes.c_size_t, W.UINT, ctypes.c_void_p]
        self.user.GetMessageW.argtypes = [ctypes.POINTER(W.MSG), W.HWND, W.UINT, W.UINT]
        self.user.TranslateMessage.argtypes = [ctypes.POINTER(W.MSG)]
        self.user.IsDialogMessageW.argtypes = [W.HWND, ctypes.POINTER(W.MSG)]
        self.user.DispatchMessageW.argtypes = [ctypes.POINTER(W.MSG)]
        self.user.DispatchMessageW.restype = LRESULT
        self.kernel.GetModuleHandleW.argtypes = [W.LPCWSTR]
        self.kernel.GetModuleHandleW.restype = W.HMODULE
        self.instance = self.kernel.GetModuleHandleW(None)
        self.callback = WNDPROC(self.dispatch)

        class WindowClass(ctypes.Structure):
            _fields_ = [('style', W.UINT), ('proc', WNDPROC), ('class_extra', ctypes.c_int),
                        ('window_extra', ctypes.c_int), ('instance', W.HINSTANCE),
                        ('icon', W.HICON), ('cursor', W.HANDLE), ('background', W.HBRUSH),
                        ('menu_name', W.LPCWSTR), ('class_name', W.LPCWSTR)]

        wc = WindowClass()
        wc.proc = self.callback
        wc.instance = self.instance
        wc.background = 6
        wc.class_name = 'TakeoffDesktopWindow'
        self.user.RegisterClassW.argtypes = [ctypes.POINTER(WindowClass)]
        if not self.user.RegisterClassW(ctypes.byref(wc)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.handle = self.user.CreateWindowExW(0, wc.class_name, 'Takeoff Assistant 실행기',
                                                0x00CA0000, -2147483648, -2147483648,
                                                800, 706, None, None, self.instance, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.controls = {}
        self.actions = {}
        self.add('STATIC', 'Takeoff Assistant · 로컬 산출 보조', 'heading', 24, 20, 740, 26)
        self.add('STATIC', '127.0.0.1 전용 · 자동 결과는 사용자 검토가 필요한 초안입니다.', 'intro', 24, 55, 740, 26)
        self.add('STATIC', '준비됨 · 시작을 누르면 로컬 서버와 작업 화면을 엽니다.', 'status', 24, 90, 740, 66)
        self.button('시작', 'start', 24, 170, 160, owner.start)
        self.button('안전 종료', 'stop', 200, 170, 160, owner.stop)
        self.button('작업 화면 열기', 'browser', 376, 170, 180, owner.open_browser)
        self.button('외부 설정 파일 선택 (선택 사항)', 'env', 24, 222, 360, owner.choose_env)
        self.button('설정 파일 선택 해제', 'clear_env', 400, 222, 220, owner.clear_env)
        self.add('STATIC', '설정 파일 없음 · 키가 없으면 로컬 검색·계산·Excel을 사용합니다.', 'env_status', 24, 264, 740, 42)
        identifier = self.add('BUTTON', '검색 모델을 이미지 판독에도 사용 (이미지 입력 지원 필요)',
                              'vision', 24, 306, 740, 26, 0x00010000 | 0x0002)
        self.actions[identifier] = owner.toggle_vision
        self.add('STATIC', '기본 꺼짐 · 별도 판독 모델은 유지 · 설정 파일 미수정 · 실제 전송은 작업 화면에서 확인',
                 'vision_help', 24, 336, 740, 26)
        self.add('EDIT', '', 'storage', 24, 366, 740, 140,
                 0x00800000 | 0x00200000 | 0x0004 | 0x0800)
        self.add('STATIC', '종료 전 브라우저에서 저장 완료를 확인하세요. 창의 ×도 안전 종료합니다.\r\n'
                 '안전 종료 완료 뒤 DB·업로드·이미지·Excel을 함께 백업하세요.\r\n'
                 '종료 중에는 창을 강제 종료하지 마세요. 저장 요청을 최대 25초 기다립니다.',
                 'help', 24, 524, 740, 76)
        self.button('백업·복구와 오류 해결 안내', 'docs', 24, 612, 360, owner.open_docs)
        self.enable('stop', False)
        self.enable('browser', False)
        self.user.SetTimer(self.handle, 1, 100, None)

    def add(self, kind, text, name, x, y, width, height, style=0):
        identifier = len(self.controls) + 100
        handle = self.user.CreateWindowExW(0, kind, text, 0x50000000 | style,
                                           x, y, width, height, self.handle, identifier, self.instance, None)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.controls[name] = handle
        gdi = ctypes.WinDLL('gdi32')
        gdi.GetStockObject.restype = W.HANDLE
        font = gdi.GetStockObject(17)
        self.user.SendMessageW(handle, 0x0030, font, 1)
        return identifier

    def button(self, text, name, x, y, width, action):
        identifier = self.add('BUTTON', text, name, x, y, width, 36, 0x00010000)
        self.actions[identifier] = action

    def text(self, name, text):
        self.user.SetWindowTextW(self.controls[name], text)

    def enable(self, name, enabled):
        self.user.EnableWindow(self.controls[name], enabled)

    def checked(self, name, checked):
        self.user.SendMessageW(self.controls[name], 0x00F1, int(checked), 0)  # BM_SETCHECK

    def message(self, title, text):
        self.user.MessageBoxW(self.handle, text, title, 0x40)

    def choose_file(self):
        class OpenFileName(ctypes.Structure):
            _fields_ = [('size', W.DWORD), ('owner', W.HWND), ('instance', W.HINSTANCE),
                        ('filter', W.LPCWSTR), ('custom_filter', W.LPWSTR), ('max_custom', W.DWORD),
                        ('filter_index', W.DWORD), ('file', W.LPWSTR), ('max_file', W.DWORD),
                        ('file_title', W.LPWSTR), ('max_file_title', W.DWORD), ('initial_dir', W.LPCWSTR),
                        ('title', W.LPCWSTR), ('flags', W.DWORD), ('file_offset', W.WORD),
                        ('file_extension', W.WORD), ('default_extension', W.LPCWSTR),
                        ('custom_data', W.LPARAM), ('hook', ctypes.c_void_p), ('template', W.LPCWSTR),
                        ('reserved', ctypes.c_void_p), ('reserved_word', W.DWORD), ('flags_ex', W.DWORD)]
        buffer = ctypes.create_unicode_buffer(32768)
        info = OpenFileName()
        info.size = ctypes.sizeof(info)
        info.owner = self.handle
        info.filter = '설정 파일 (*.env)\0*.env\0모든 파일\0*.*\0\0'
        info.file = ctypes.cast(buffer, W.LPWSTR)
        info.max_file = len(buffer)
        info.title = '복사하지 않고 읽을 외부 UTF-8 설정 파일'
        info.flags = 0x1000 | 0x800 | 0x8
        dll = ctypes.WinDLL('comdlg32')
        dll.GetOpenFileNameW.argtypes = [ctypes.POINTER(OpenFileName)]
        return buffer.value if dll.GetOpenFileNameW(ctypes.byref(info)) else None

    def dispatch(self, handle, message, wparam, lparam):
        try:
            if message == 0x0111:
                action = self.actions.get(wparam & 0xFFFF)
                if action:
                    action()
                    return 0
            elif message == 0x0113:
                self.owner.poll()
                return 0
            elif message == 0x0010:
                self.owner.close()
                return 0
            elif message == 0x0002:
                self.user.PostQuitMessage(0)
                return 0
        except Exception:
            if hasattr(self, 'controls') and 'status' in self.controls:
                self.text('status', '실행기 오류가 발생했습니다. 창을 닫아 안전 종료한 뒤 다시 실행하세요.')
            return 0
        return self.user.DefWindowProcW(handle, message, wparam, lparam)

    def destroy(self):
        self.user.DestroyWindow(self.handle)

    def run(self):
        self.user.ShowWindow(self.handle, 5)
        message = W.MSG()
        while self.user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if not self.user.IsDialogMessageW(self.handle, ctypes.byref(message)):
                self.user.TranslateMessage(ctypes.byref(message))
                self.user.DispatchMessageW(ctypes.byref(message))
