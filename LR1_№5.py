dict_5 = {f'{m}': m for m in range(1, 10)} #заполнение словаря через "генератор-словаря"
def func_filter(dict_0):
    print(f'Исходный словарь {dict_0}')
    list = []
    for key in dict_0: #Проверка словаря на условия:
        list.append(key)
    for key in dict_0:
        if not isinstance(key,str): #является ли ключ текстом
            print(f'ключ: {key} не является текстом')
            return dict_0
        else:
            if not isinstance(dict_0[key], int): #является ли значение целочисленным значением
                print(f'значение: {dict_0[key]} не является целым')
                return dict_0
    values = []
    for i in dict_0.values():
        values.append(i)
    values.sort()
    n = len(values)
    if n % 2 == 1:
        median = values[n // 2]
        print(f"Медиана = {median} (элемент на позиции {n // 2})")
    else:
        median = (values[n // 2 - 1] + values[n // 2]) / 2
        print(f"Медиана = {median}")
    filtered_dict = dict(filter(lambda item: item[1] >= median, dict_0.items()))
    return filtered_dict

print(func_filter(dict_5))
