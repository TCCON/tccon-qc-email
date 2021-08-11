from pathlib import Path
import shutil


def backup_file_rolling(file, n_backups=5):
    # first figure out how long the extension needs to be
    w = len(str(n_backups))
    fmt = '{{}}.{{:{}d}}'.format(w)

    for i in range(n_backups-1, 0, -1):
        backup_file = Path(fmt.format(file, i))
        if backup_file.exists():
            new = fmt.format(file, i+1)
            shutil.move(str(backup_file), new)

    shutil.move(file, fmt.format(file, 1))
