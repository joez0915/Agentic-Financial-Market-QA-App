from openai import OpenAI
from .agent_types import safe_text


class Context_Rewriter_Agent:
    def __init__(self, openai_client):
        self.client: OpenAI = openai_client
        self.prompt = (
            "You rewrite the user's latest query into ONE standalone, concrete question when needed. The output MUST contain the explicit topic (not just 'it' or 'they') so that retrieval can use it.\n"
            "IMPORTANT: If the user's message is a fragment, a single word, or too vague (e.g. 'see', 'I love', 'ok'), "
            "do NOT invent a new question. Return the user's message UNCHANGED.\n"
            "For multi-turn follow-ups, ALWAYS resolve pronouns to the concrete topic from history. Examples:\n"
            "- 'Why is it important?' (after discussing cross-validation) -> 'Why is cross-validation important?'\n"
            "- 'How do they learn?' (after discussing neural networks) -> 'How do neural networks learn?'\n"
            "- 'Can you give a simple example?' (after logistic regression) -> 'Can you give a simple example of logistic regression?'\n"
            "- 'What are some ways to prevent it?' (after overfitting) -> 'What are some ways to prevent overfitting?'\n"
            "- 'How does this affect model selection?' (after bias-variance) -> 'How does the bias-variance tradeoff affect model selection?'\n"
            "Do NOT answer the question. Only output the rewritten question with the topic filled in, or the original message unchanged if no rewriting is needed.\n"
        )

    def rephrase(self, user_history, latest_query):
        history_text = ""
        for m in (user_history or [])[-8:]:
            role = m.get("role", "user")
            content = m.get("content", "")
            history_text += f"{role.upper()}: {content}\n"

        resp = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            temperature=0,
            messages=[
                {"role": "system", "content": self.prompt},
                {
                    "role": "user",
                    "content": f"Conversation:\n{history_text}\n\nLatest query:\n{safe_text(latest_query)}",
                },
            ],
        )
        return resp.choices[0].message.content.strip()
