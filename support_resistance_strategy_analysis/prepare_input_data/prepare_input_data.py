from prepare_input_data.prepare_file_forexter import prepareFileForexter
import os



class PrepareInputData:
    def __init__(self, input_path: str, output_path: str):

        print("==== Prepare Input Data ====")
        self.input_path = input_path
        self.output_path = output_path
        self.__prepareAllFiles()

    def __findFiles(self):
        return [f for f in os.listdir(self.input_path) if f.endswith('.txt')]

    def __prepareAllFiles(self):
        self.__prepareAllFiles_15m()
        self.__prepareAllFiles_1H()
        self.__prepareAllFiles_1D()
        self.__prepareAllFiles_1W()
        self.__prepareAllFiles_MN()

    def __prepareAllFiles_15m(self):
        files = self.__findFiles()
        for file in files:
            input_file_path = os.path.join(self.input_path, file)
            print(f"Processing file: {input_file_path}")
            file = file.replace('.txt', '_15m.txt')
            output_file_path = os.path.join(self.output_path, file)
            prepareFileForexter(input_file_path, output_file_path)
            print(f"Finished processing file: {output_file_path}\n")

    def __prepareAllFiles_1H(self):
        files = self.__findFiles()
        for file in files:
            input_file_path = os.path.join(self.input_path, file)
            print(f"Processing file: {input_file_path}")
            file = file.replace('.txt', '_1H.txt')
            output_file_path = os.path.join(self.output_path, file)
            prepareFileForexter(input_file_path, output_file_path, '1H')
            print(f"Finished processing file: {output_file_path}\n")

    def __prepareAllFiles_1D(self):
        files = self.__findFiles()
        for file in files:
            input_file_path = os.path.join(self.input_path, file)
            print(f"Processing file: {input_file_path}")
            file = file.replace('.txt', '_1D.txt')
            output_file_path = os.path.join(self.output_path, file)
            prepareFileForexter(input_file_path, output_file_path, '1D')
            print(f"Finished processing file: {output_file_path}\n")

    def __prepareAllFiles_1W(self):
        files = self.__findFiles()
        for file in files:
            input_file_path = os.path.join(self.input_path, file)
            print(f"Processing file: {input_file_path}")
            file = file.replace('.txt', '_1W.txt')
            output_file_path = os.path.join(self.output_path, file)
            prepareFileForexter(input_file_path, output_file_path, '1W')
            print(f"Finished processing file: {output_file_path}\n")

    def __prepareAllFiles_MN(self):
        files = self.__findFiles()
        for file in files:
            input_file_path = os.path.join(self.input_path, file)
            print(f"Processing file: {input_file_path}")
            file = file.replace('.txt', '_MN.txt')
            output_file_path = os.path.join(self.output_path, file)
            prepareFileForexter(input_file_path, output_file_path, '1M')
            print(f"Finished processing file: {output_file_path}\n")


    def __call__(self):
        self.__prepareAllFiles()