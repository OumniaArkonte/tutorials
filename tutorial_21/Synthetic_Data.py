import pandas as pd
from sdv.metadata import Metadata
from sdv.single_table import GaussianCopulaSynthesizer
from sdv.evaluation.single_table import evaluate_quality, run_diagnostic, get_column_plot


# =========================
# Agent 1 : Planner
# =========================
class PlannerAgent:
    def __init__(self):
        self.objective = None

    def choose_objective(self):
        print("""
         Choose the objective for synthetic data generation:
            1. Schema replication
            2. Realism + variety
            3. Narrative fields
        """)
        choice = input("Your choice (1/2/3): ")

        if choice == '1':
            self.objective = "Schema replication"
        elif choice == '2':
            self.objective = "Realism + variety"
        elif choice == '3':
            self.objective = "Narrative fields"
        else:
            print(" Invalid choice, defaulting to Schema replication")
            self.objective = "Schema replication"

        print(f" Objective selected: {self.objective}")
        return self.objective


# =========================
# Agent 2 : Generator
# =========================
class GeneratorAgent:
    def __init__(self, metadata, real_data):
        self.metadata = metadata
        self.real_data = real_data
        self.synthetic_data = None

    def generate_data(self, num_rows=500):
        print(" Agent 2 (Generator): Training synthesizer...")
        synthesizer = GaussianCopulaSynthesizer(self.metadata)
        synthesizer.fit(self.real_data)

        print(f" Agent 2 (Generator): Generating {num_rows} synthetic rows...")
        self.synthetic_data = synthesizer.sample(num_rows=num_rows)
        self.synthetic_data.to_csv("Data/synthetic_data.csv", index=False)

        print(" Synthetic data generated and saved to Data/synthetic_data.csv")
        return self.synthetic_data


# =========================
# Agent 3 : Analyst 
# =========================
import plotly.io as pio
pio.renderers.default = "browser" 

class AnalystAgent:
    def __init__(self, real_data, synthetic_data, metadata):
        self.real_data = real_data
        self.synthetic_data = synthetic_data
        self.metadata = metadata

    def run_diagnostics(self):
        print("\n Agent 3 (Analyst): Running diagnostic report...")
        diagnostic = run_diagnostic(
            real_data=self.real_data,
            synthetic_data=self.synthetic_data,
            metadata=self.metadata
        )
        print(diagnostic)

    def quality_report(self):
        print("\n Agent 3 (Analyst): Generating quality report...")
        quality = evaluate_quality(
            real_data=self.real_data,
            synthetic_data=self.synthetic_data,
            metadata=self.metadata
        )
        print(quality.get_details("Column Shapes"))

    def visualize_column(self, column_name="PreferedOrderCat"):
        print(f"\n Agent 3 (Analyst): Visualizing column '{column_name}'...")
        fig = get_column_plot(
            real_data=self.real_data,
            synthetic_data=self.synthetic_data,
            column_name=column_name,
            metadata=self.metadata
        )
    
        fig.show()




# =========================
# Main Orchestration
# =========================
if __name__ == "__main__":
    print(" Demo N°18: AI Agent to Create Synthetic Data")

    # Load real data
    print("\n Loading real dataset...")
    real_data = pd.read_csv("Data/E-Commerce Dataset.csv", nrows=500)
    print(" Real data loaded with shape:", real_data.shape)

    planner = PlannerAgent()
    objective = planner.choose_objective()

    if objective == "Narrative fields":
        print(" Narrative fields require NLP text generation models (not covered in this demo).")
    elif objective == "Schema replication":
        print(" Only Schema replication selected. You can run Generator and Analyst separately later.")
    else:
        print(" This option will run full pipeline.")

    # Menu interactif pour lancer les agents manuellement
    while True:
        print("\n Choose agent to run:")
        print("1. Planner (choose objective)")
        print("2. Generator (create synthetic data)")
        print("3. Analyst (evaluate synthetic data)")
        print("4. Exit")

        choice = input("Your choice (1/2/3/4): ")

        if choice == "1":
            objective = planner.choose_objective()
        elif choice == "2":
            if not planner.objective:
                print(" First choose an objective with Planner!")
                continue
            metadata = Metadata.detect_from_dataframe(real_data)
            generator = GeneratorAgent(metadata, real_data)
            synthetic_data = generator.generate_data(num_rows=500)
        elif choice == "3":
            try:
                synthetic_data  
            except NameError:
                print(" Generate synthetic data first!")
                continue
            analyst = AnalystAgent(real_data, synthetic_data, metadata)
            analyst.run_diagnostics()
            analyst.quality_report()
            analyst.visualize_column("PreferedOrderCat")
        elif choice == "4":
            print(" Exiting.")
            break
        else:
            print(" Invalid choice.")
