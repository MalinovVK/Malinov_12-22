def func(min, max, step): #Функция
    list = [i for i in range(min, max+1, step)] #Генератор списка
    print(list) #Вывод сгенерированного списка
    for i in list: #Если число четное, то вычислить корень из суммы квадратов чисел
        if i % 2 == 0:
            sum=+i**2
    sum_sqrt = (sum)**0.5
    print(sum_sqrt)
    numbers = range(min, max + 1)
    result = set(filter(lambda x: x % 2 != 0 and x % 3 == 0, numbers)) #Генерирует множество из нечетных чисел кратных 3
    return result

print(func(0,30,2))