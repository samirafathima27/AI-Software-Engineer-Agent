def calculate_total(price, quantity):
    return price * quantity

def calculate_discount(price, discount_percent):
    return price * (1 - discount_percent / 100)

def calculate_final_price(price, discount_percent):
    return calculate_discount(price, discount_percent)