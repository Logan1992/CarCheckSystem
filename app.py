from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import openai

# Configura a chave da API da OpenAI
client = openai.OpenAI(api_key="sua-chave-api")

app = Flask(__name__)

class VehicleDiagnosticSystem:
    def __init__(self, csv_file):
        self.codes = self.load_codes(csv_file)
        self.diagnostics_history = []

    def load_codes(self, csv_file):
        try:
            df = pd.read_csv(csv_file)
            if 'Code' in df.columns and 'Description' in df.columns:
                codes = dict(zip(df['Code'], df['Description']))
            else:
                raise KeyError("As colunas 'Code' ou 'Description' não foram encontradas no arquivo CSV.")
            return codes
        except FileNotFoundError:
            print(f"Arquivo {csv_file} não encontrado.")
            return {}

    def search_code(self, code):
        description = self.codes.get(code.upper(), None)
        if description:
            return f"Código: {code.upper()}\nDescrição: {description}"
        else:
            return f"Código {code.upper()} não encontrado."

    def diagnose_vehicle(self, customer_complaint, method_choice, dtc_code, related_symptoms, problem_area):
        diagnostic_methods = [
            "Verificar a Reclamação",
            "Determinar os Sintomas Relacionados",
            "Analisar os Sintomas Relacionados",
            "Isolar a Área do Problema",
            "Reparar a Área do Problema",
            "Certificar que a Operação Está Adequada"
        ]
        selected_method = diagnostic_methods[method_choice - 1]
        dtc_description = self.search_code(dtc_code) if dtc_code else "N/A"

        diagnosis = {
            "Reclamação do Cliente": customer_complaint,
            "Método de Diagnóstico": selected_method,
            "Código de Falha": dtc_code,
            "Descrição do Código": dtc_description,
            "Sintomas Relacionados": related_symptoms,
            "Área do Problema": problem_area
        }
        self.diagnostics_history.append(diagnosis)

        return self.get_chatbot_solution(diagnosis)

    def get_chatbot_solution(self, diagnosis):
        assistant = client.beta.assistants.create(
            name="Vehicle Diagnostic Assistant",
            instructions="You are a vehicle diagnostic assistant. Provide the most accurate vehicle problem diagnosis and solutions.",
            tools=[{"type": "code_interpreter"}],
            model="gpt-4-1106-preview",
        )

        thread = client.beta.threads.create()

        prompt = (
            f"Cliente reclamou de: {diagnosis['Reclamação do Cliente']}\n"
            f"Método de Diagnóstico: {diagnosis['Método de Diagnóstico']}\n"
            f"Código de Falha: {diagnosis['Código de Falha']}\n"
            f"Descrição do Código: {diagnosis['Descrição do Código']}\n"
            f"Sintomas Relacionados: {diagnosis['Sintomas Relacionados']}\n"
            f"Área do Problema: {diagnosis['Área do Problema']}\n"
            f"Com base nessas informações, quais podem ser as causas do problema e como ele pode ser resolvido?"
        )

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt,
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions="Please address the user as 'Mechanic'.",
        )

        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            suggestion = "\n".join([msg.content[0].text.value for msg in messages if msg.content[0].type == "text"])
        else:
            suggestion = "Ocorreu um erro ao processar a solicitação. Tente novamente."

        client.beta.assistants.delete(assistant.id)

        return suggestion

# Inicializa o sistema de diagnóstico
system = VehicleDiagnosticSystem('OBD.csv')

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        customer_complaint = request.form.get("customer_complaint")
        method_choice = int(request.form.get("method_choice"))
        dtc_code = request.form.get("dtc_code")
        related_symptoms = request.form.get("related_symptoms")
        problem_area = request.form.get("problem_area")

        result = system.diagnose_vehicle(customer_complaint, method_choice, dtc_code, related_symptoms, problem_area)
        return render_template("result.html", result=result)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
