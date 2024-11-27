def find_missing_number(start: int, end: int, existed: set):
    i = start
    while i <= end:
        if i not in existed:
            return i
        i = i + 1
    return None


def find_missing(arr: list, existed: set):
    i = 0
    end = len(arr)
    while i < end:
        value = arr[i]
        if value not in existed:
            return value
        i = i + 1
    return None
