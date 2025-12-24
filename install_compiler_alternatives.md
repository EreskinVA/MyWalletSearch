# Альтернативные способы установки компилятора

Если MSYS2 установка слишком медленная, попробуйте эти варианты:

## Вариант 1: Установка только GCC без обновления системы

В MSYS2 MinGW 64-bit попробуйте установить только компилятор без полного обновления:

```bash
# Пропустить обновление системы, установить только GCC
pacman -S mingw-w64-x86_64-gcc --noconfirm
```

## Вариант 2: Использовать другой зеркал

1. Откройте файл: `C:\msys64\etc\pacman.d\mirrorlist.mingw64`
2. Раскомментируйте (уберите `#`) зеркало ближе к вам:
   - Германия: `Server = https://mirror.fcix.net/msys2/mingw/x86_64`
   - Япония: `Server = https://mirrors.cat.net/msys2/mingw/x86_64`
   - Китай: `Server = https://mirrors.tuna.tsinghua.edu.cn/msys2/mingw/x86_64`
3. Или запустите скрипт: `.\fix_msys2_mirrors.ps1`

## Вариант 3: WinLibs (прямая установка MinGW)

1. Скачайте WinLibs: https://winlibs.com/
2. Выберите: GCC 13.x (или новее) + MinGW-w64 UCRT
3. Распакуйте в `C:\MinGW`
4. Добавьте `C:\MinGW\bin` в PATH

## Вариант 4: TDM-GCC

1. Скачайте: https://jmeubank.github.io/tdm-gcc/
2. Установите (автоматически добавит в PATH)

## Вариант 5: Visual Studio Build Tools (офлайн установка)

1. Скачайте Visual Studio Build Tools
2. Выберите "Desktop development with C++"
3. Можно скачать офлайн установщик для установки без интернета

## Вариант 6: Использовать уже установленный компилятор

Проверьте, может быть компилятор уже установлен:

```powershell
# Проверка
.\setup_compiler.ps1

# Или вручную
where.exe g++
where.exe gcc
```

## Вариант 7: WSL (Windows Subsystem for Linux)

Если у вас установлен WSL, можно собрать там:

```bash
# В WSL
sudo apt update
sudo apt install build-essential
cd /mnt/c/Users/User/Desktop/vanity/projectCode/MyWalletSearch
make clean
make gpu=1 CCAP=6.1 all
```

## Рекомендация

Если интернет медленный:
1. Попробуйте `fix_msys2_mirrors.ps1` для настройки быстрых зеркал
2. Или используйте WinLibs (прямая загрузка, без пакетного менеджера)
3. Или установите Visual Studio Build Tools (можно офлайн)


