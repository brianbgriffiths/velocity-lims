from settings.velocity import VelocityScript
import random

class Script(VelocityScript):
    def run(self):
        print(f"Running script for step {self.step}!")

        random_number = random.randint(1, 100)  # Generates a random number between 1 and 100
        print(random_number)

        self.step.clear_routes()

        fail_count = 0
        for output in self.outputs:
            print(output.id)
            output.rand_num=random.randint(1, 100)
            if output.rand_num > 50:
                print(output.rand_num,'fail')
                output.qc_status='Fail'
                output.route_to('repeat_step')
                fail_count+=1
            else:
                print(output.rand_num,'pass')
                output.qc_status='Pass'
                output.route_to('next_step')

        self.outputs.commit()
        

        self.return_message = f"Failed {fail_count} samples above threshold of 50 ({fail_count/len(self.outputs)*100:.0f}%)."

        return self.complete()
        
    
    
    
        
        


