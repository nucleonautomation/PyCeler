def Sources():  # Test support/workload for random boundary.
    Header = 'import numpy as np\nimport random\nOutput = np.zeros((8, 4))\nRow = -9\n'
    Cases = {
        'Zero_Step': 'Step = 0\nfor Row in range(8):\n    for Column in range(0, 4, Step):\n        Output[Row, Column] = random.random()\n',
        'Empty_Outer': 'Step = 0\nfor Row in range(0):\n    for Column in range(0, 4, Step):\n        Output[Row, Column] = random.random()\n',
        'Empty_Middle': 'Step = 0\nfor Row in range(8):\n    for Middle in range(0):\n        for Column in range(0, 4, Step):\n            Output[Row, Column] = random.random()\n',
        'Valid_Step': 'Step = 1\nfor Row in range(8):\n    for Column in range(0, 4, Step):\n        Output[Row, Column] = random.random()\n',
        'Short_Circuit': 'for Row in range(8):\n    for Column in range(4):\n        Output[Row, Column] = random.random() if Row < 3 and random.random() < 0.5 or random.random() < 0.2 else 0.5\n',
        'Lazy_True': 'for Row in range(8):\n    for Column in range(4):\n        Output[Row, Column] = 0.5 if Row < 9 or random.random() < 0.5 else random.random()\n',
        'Lazy_False': 'for Row in range(8):\n    for Column in range(4):\n        Output[Row, Column] = random.random() if Row < 0 and random.random() < 0.5 else 0.5\n',
        'Negative_Step': 'Step = -1\nfor Row in range(8):\n    for Column in range(3, -1, Step):\n        Output[Row, Column] = random.random()\n',
    }
    return {Name: Header + Body for Name, Body in Cases.items()}
