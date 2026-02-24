def func_parol(string):
    if len(string) >= 8:
        if any(tx.isdigit() for tx in string):
            if any(tx.isupper() for tx in string):
                if any(tx.islower() for tx in string):
                    True
                    return f'Пароль безопасен'
                else:
                    return f'Добавьте нижний регистр'
            else:
                return f'Добавьте верхний регистр'
        else:
            return f'Добавьте число'
    else:
        return f'Пароль менее 8 символов'


text=input("Напишите пароль: ")
print(func_parol(text))
