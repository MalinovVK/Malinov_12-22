one_set={i for i in range(1,11)} #Задание #1
print(one_set)

list_two=[] #Задание №2
for num in one_set:
    if num % 3 == 0:
        list_two.append(num*4)
    else:
        list_two.append(num+6)
print(list_two)

dict_3 = dict(zip(one_set,list_two)) #Задание №3
print(dict_3)

def func_find(list, x): #Задание №4
    for i in range(len(list)):
        if list[i]==x:
            return f'Элемент: {x}, позиция: {i}'
    else:
        return f'Элемент не найден'

print(func_find(list_two, 24))




