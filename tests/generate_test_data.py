import os
import shutil
import tempfile
import time

def create_sample_duplicates(base_dir: str):
    folder_a = os.path.join(base_dir, "FolderA", "Sub1")
    folder_b = os.path.join(base_dir, "FolderB", "Sub2")
    folder_c = os.path.join(base_dir, "FolderC")

    os.makedirs(folder_a, exist_ok=True)
    os.makedirs(folder_b, exist_ok=True)
    os.makedirs(folder_c, exist_ok=True)

    # 1. Duplicate Group 1: 3 text files with varying timestamps
    data1 = b"Sample text duplicate content for Windedup tests!\r\n" * 150
    path1_a = os.path.join(folder_a, "report.txt")
    path1_b = os.path.join(folder_b, "report_copy.txt")
    path1_c = os.path.join(folder_c, "backup_report.txt")

    for p in (path1_a, path1_b, path1_c):
        with open(p, "wb") as f:
            f.write(data1)

    now = time.time()
    os.utime(path1_a, (now - 3600, now - 3600))  # Oldest
    os.utime(path1_b, (now - 1800, now - 1800))  # Mid
    os.utime(path1_c, (now, now))                # Newest

    # 2. Duplicate Group 2: Binary duplicate pair (>64KB to test chunked hashing)
    data2 = b"BINARY_DATA_CHUNK_" * 5000  # ~85 KB
    path2_a = os.path.join(folder_a, "graphic_asset.dat")
    path2_b = os.path.join(folder_b, "graphic_asset_duplicate.dat")

    with open(path2_a, "wb") as f:
        f.write(data2)
    with open(path2_b, "wb") as f:
        f.write(data2)

    # 3. Unique files (different content, one with same size as group 1 to test hash collision filter)
    unique1 = b"Unique content completely different!" * 50
    with open(os.path.join(base_dir, "unique_file.txt"), "wb") as f:
        f.write(unique1)

    # File with identical size to data1 but different content
    collision_size_data = b"X" * len(data1)
    with open(os.path.join(folder_c, "same_size_diff_content.txt"), "wb") as f:
        f.write(collision_size_data)

    print(f"Sample duplicate test tree generated at: {base_dir}")
    return base_dir

if __name__ == "__main__":
    target = os.path.join(tempfile.gettempdir(), "windedup_sample_test")
    if os.path.exists(target):
        shutil.rmtree(target)
    create_sample_duplicates(target)
