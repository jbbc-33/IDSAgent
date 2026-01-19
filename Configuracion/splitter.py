import pandas as pd

PATH_DATA= "/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/data/"
PATH_TRAIN_CSV= "train-logs-dataset.csv"
PATH_TEST_CSV= "test-logs-dataset.csv"

if __name__ == "__main__":
    train_csv = pd.read_csv(PATH_DATA+PATH_TRAIN_CSV)

    mitad = len(train_csv) // 2

    train_csv.iloc[mitad:].to_csv(PATH_DATA+"1-train-logs-dataset.csv")
    train_csv.iloc[:mitad].to_csv(PATH_DATA+"2-train-logs-dataset.csv")

    test_csv = pd.read_csv(PATH_DATA+PATH_TEST_CSV)

    mitad = len(test_csv) // 2

    test_csv.iloc[mitad:].to_csv(PATH_DATA+"1-test-logs-dataset.csv")
    test_csv.iloc[:mitad].to_csv(PATH_DATA+"2-test-logs-dataset.csv")