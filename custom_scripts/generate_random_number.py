from settings.velocity import VelocityScript
import random

class Script(VelocityScript):
    def run(self):
        print(f"Running script for step {self.step}!")

        random_number = random.randint(1, 100)  # Generates a random number between 1 and 100
        print(random_number)

        for output in self.outputs:
            print(output.id)
            output.rand_num=random.randint(1, 100)

        self.outputs.commit()

        self.return_message = f"Here's a bonus random number: {random_number}"

        return self.complete()
        
    
    
    
        
        


