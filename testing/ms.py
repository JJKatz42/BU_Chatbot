def find_all(to_find, lst):
    count = 0
    True_or_False = True
    for i in to_find:
        i_in_lst = False
        for n in lst:
            if i == n:
                count += 1
                i_in_lst = True
        if i_in_lst == False:
            True_or_False = False

    return count, True_or_False


print(find_all([2, 3], [2, 3, 2]) == (3, True))

print(find_all([2, 3, 5], [5, 5, 3, 7]) == (3, False))
