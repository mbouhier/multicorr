import logging
import datetime

import sys
#a pointer to the module object instance itself.
this = sys.modules[__name__]



# self.logger.basicConfig(level=self.logger.DEBUG,
#                    format='(%(threadName)-9s) %(message)s',)

logging.basicConfig(level  = logging.DEBUG,
                    format = '%(message)s', )

logging.basicConfig(level  = logging.ERROR,
                    format = 'Method "%(funcName)s()" (l.%(lineno)s): \n%(message)s', )

# on affiche que les logging critiques de QT, sinon il y en a trop
for name, logger in logging.root.manager.loggerDict.items():
    # print name
    # pass
    logger.disabled = True

# ==============================================================================




class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[32m'
    WARNING = '\033[93m'
    FAIL = '\033[31m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    INFO = '\033[95m'
    UNDERLINE = '\033[4m'
    NORMAL = '\033[99m'

# Red = '\033[91m'
# Green = '\033[92m'
# Blue = '\033[94m'
# Cyan = '\033[96m'
# White = '\033[97m'
# Yellow = '\033[93m'
# Magenta = '\033[95m'
# Grey = '\033[90m'
# Black = '\033[90m'
# Default = '\033[99m'

    # ResetAll = "\033[0m"
    #
    # Bold       = "\033[1m"
    # Dim        = "\033[2m"
    # Underlined = "\033[4m"
    # Blink      = "\033[5m"
    # Reverse    = "\033[7m"
    # Hidden     = "\033[8m"
    #
    # ResetBold       = "\033[21m"
    # ResetDim        = "\033[22m"
    # ResetUnderlined = "\033[24m"
    # ResetBlink      = "\033[25m"
    # ResetReverse    = "\033[27m"
    # ResetHidden     = "\033[28m"
    #
    # Default      = "\033[39m"
    # Black        = "\033[30m"
    # Red          = "\033[31m"
    # Green        = "\033[32m"
    # Yellow       = "\033[33m"
    # Blue         = "\033[34m"
    # Magenta      = "\033[35m"
    # Cyan         = "\033[36m"
    # LightGray    = "\033[37m"
    # DarkGray     = "\033[90m"
    # LightRed     = "\033[91m"
    # LightGreen   = "\033[92m"
    # LightYellow  = "\033[93m"
    # LightBlue    = "\033[94m"
    # LightMagenta = "\033[95m"
    # LightCyan    = "\033[96m"
    # White        = "\033[97m"
    #
    # BackgroundDefault      = "\033[49m"
    # BackgroundBlack        = "\033[40m"
    # BackgroundRed          = "\033[41m"
    # BackgroundGreen        = "\033[42m"
    # BackgroundYellow       = "\033[43m"
    # BackgroundBlue         = "\033[44m"
    # BackgroundMagenta      = "\033[45m"
    # BackgroundCyan         = "\033[46m"
    # BackgroundLightGray    = "\033[47m"
    # BackgroundDarkGray     = "\033[100m"
    # BackgroundLightRed     = "\033[101m"
    # BackgroundLightGreen   = "\033[102m"
    # BackgroundLightYellow  = "\033[103m"
    # BackgroundLightBlue    = "\033[104m"
    # BackgroundLightMagenta = "\033[105m"
    # BackgroundLightCyan    = "\033[106m"
    # BackgroundWhite        = "\033[107m"

this.log_path = None

def setPath( path):

    now = datetime.datetime.now()

    this.log_path = path + "//log_%s.txt" % (now.strftime("%Y_%m_%d_%H_%M_%S"))

    with open(this.log_path, 'w+') as f:
        f.write("LOGFILE CREATED ON %s\n\n" % (now.strftime("%d-%m-%Y at %H:%M:%S")))

    info("recording log to %s" % (this.log_path,))

def _writeToFile(level, txt):
    if this.log_path:
        with open(this.log_path, 'a') as f:
            date_time_stamp = datetime.datetime.now().strftime("%H:%M:%S")
            f.write("\n" + date_time_stamp + "\t" + level + "\t" + txt)


def header(*args):
    txt = " ".join( [repr(a) for a in args] )
    print(bcolors.HEADER + txt + bcolors.ENDC)
    _writeToFile("HEADER", txt)

def debug(*args):
    txt = " ".join([repr(a) for a in args])
    print(bcolors.GREEN + txt + bcolors.ENDC)
    _writeToFile("DEBUG", txt)

def warning(*args):
    txt = " ".join([repr(a) for a in args])
    print(bcolors.WARNING + txt + bcolors.ENDC)
    _writeToFile("WARNING", txt)

def error(*args):
    txt = " ".join([repr(a) for a in args])
    print(bcolors.FAIL + txt + bcolors.ENDC)
    _writeToFile("ERROR", txt)

def info(*args):
    txt = " ".join([repr(a) for a in args])
    print(bcolors.INFO + txt + bcolors.ENDC)
    _writeToFile("INFO", txt)