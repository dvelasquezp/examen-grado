"""Ejercicios de lógica proposicional en lenguaje natural con contexto de Apuntes."""

import random
import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class LogicExerciseGenerator:
    """Genera ejercicios expresivos a partir de pares de conceptos en Apuntes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_exercises(self, subject_id: UUID, count: int = 8) -> list[dict]:
        pairs = await self._pairs_with_context(subject_id, limit=50)
        if not pairs:
            return self._fallback_exercises(count)

        templates = [
            self._conjunction_exercise,
            self._disjunction_exercise,
            self._necessary_condition_exercise,
            self._sufficient_condition_exercise,
            self._conjunction_truth_exercise,
            self._negation_exercise,
            self._biconditional_exercise,
        ]

        exercises: list[dict] = []
        random.shuffle(pairs)
        used_templates: set[str] = set()

        for pair in pairs:
            if len(exercises) >= count:
                break
            available = [t for t in templates if t.__name__ not in used_templates] or templates
            builder = random.choice(available)
            ex = builder(pair)
            if ex:
                used_templates.add(builder.__name__)
                exercises.append(ex)

        return exercises[:count]

    async def _pairs_with_context(self, subject_id: UUID, limit: int) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT c1.id AS id_a, c1.title AS title_a,
                       c2.id AS id_b, c2.title AS title_b,
                       COUNT(*) AS weight,
                       (
                         SELECT COALESCE(l1.excerpt, dc.content)
                         FROM concept_chunk_links l1
                         JOIN concept_chunk_links l2 ON l1.chunk_id = l2.chunk_id
                             AND l2.concept_id = c2.id
                         JOIN document_chunks dc ON dc.id = l1.chunk_id
                         WHERE l1.concept_id = c1.id
                         LIMIT 1
                       ) AS excerpt
                FROM concept_chunk_links l1
                JOIN concept_chunk_links l2 ON l1.chunk_id = l2.chunk_id
                    AND l1.concept_id < l2.concept_id
                JOIN concepts c1 ON c1.id = l1.concept_id
                JOIN concepts c2 ON c2.id = l2.concept_id
                WHERE c1.subject_id = :subject_id
                GROUP BY c1.id, c1.title, c2.id, c2.title
                HAVING COUNT(*) >= 1
                ORDER BY weight DESC
                LIMIT :limit
            """),
            {"subject_id": str(subject_id), "limit": limit},
        )
        pairs = []
        for r in result:
            excerpt = self._trim_context(r.excerpt or "")
            pairs.append(
                {
                    "id_a": str(r.id_a),
                    "title_a": r.title_a,
                    "id_b": str(r.id_b),
                    "title_b": r.title_b,
                    "weight": r.weight,
                    "context": excerpt,
                }
            )
        return pairs

    @staticmethod
    def _trim_context(text: str, max_len: int = 280) -> str:
        text = re.sub(r"\s+", " ", text.strip())
        if len(text) <= max_len:
            return text
        return text[: max_len - 1].rsplit(" ", 1)[0] + "…"

    def _base_exercise(self, pair: dict, kind: str, question: str, options: list[dict], explanation: str) -> dict:
        correct_id = next(o["id"] for o in options if o.get("correct"))
        clean_options = [{"id": o["id"], "label": o["label"]} for o in options]
        random.shuffle(clean_options)
        return {
            "id": f"{pair['id_a']}:{pair['id_b']}:{kind}:{hash(question) & 0xFFFF}",
            "kind": kind,
            "context": pair.get("context") or (
                f"En tus apuntes, «{pair['title_a']}» y «{pair['title_b']}» "
                f"aparecen mencionados en el mismo pasaje doctrinal."
            ),
            "question": question,
            "concept_a": pair["title_a"],
            "concept_b": pair["title_b"],
            "options": clean_options,
            "correct_option": correct_id,
            "explanation": explanation,
        }

    def _conjunction_exercise(self, pair: dict) -> dict:
        a, b = pair["title_a"], pair["title_b"]
        question = (
            f"Imagina que el examinador te dice: «Para que exista {b}, no basta uno solo: "
            f"deben concurrir {a} y {b} al mismo tiempo». "
            f"¿Cómo se expresa en lógica proposicional la idea de que «las dos cosas juntas» son necesarias?"
        )
        options = [
            {
                "id": "AND",
                "label": f"Ambas deben cumplirse simultáneamente: «hay {a} Y hay {b}» (conjunción)",
                "correct": True,
            },
            {
                "id": "OR",
                "label": f"Basta con que ocurra una u otra: «hay {a} O hay {b}» (disyunción)",
            },
            {
                "id": "IMPLIES_AB",
                "label": f"Si ocurre {a}, entonces necesariamente ocurre {b} (implicación)",
            },
            {
                "id": "IFF",
                "label": f"{a} y {b} se implican mutuamente «si y solo si» (bicondicional)",
            },
        ]
        explanation = (
            f"La conjunción (∧) expresa que proposiciones deben ser verdaderas a la vez. "
            f"Aquí se requiere {a} ∧ {b}: «{a} y {b}»."
        )
        return self._base_exercise(pair, "conjunction", question, options, explanation)

    def _disjunction_exercise(self, pair: dict) -> dict:
        a, b = pair["title_a"], pair["title_b"]
        question = (
            f"En el apunte se plantea un caso en que basta que se cumpla {a} o {b}, "
            f"pero no es indispensable que ocurran los dos. "
            f"¿Qué operador lógico representa «al menos una de las dos»?"
        )
        options = [
            {
                "id": "OR",
                "label": f"Con que se cumpla {a} o {b} (o ambas) alcanza (disyunción)",
                "correct": True,
            },
            {
                "id": "AND",
                "label": f"Deben cumplirse {a} y {b} obligatoriamente juntas (conjunción)",
            },
            {
                "id": "IMPLIES_AB",
                "label": f"{a} es condición necesaria para {b} (implicación)",
            },
            {
                "id": "NOT_A",
                "label": f"Ninguna de las dos puede cumplirse (negación conjunta)",
            },
        ]
        explanation = (
            f"La disyunción (∨) significa «al menos una»: {a} ∨ {b}. "
            f"No exige que ambas se cumplan simultáneamente."
        )
        return self._base_exercise(pair, "disjunction", question, options, explanation)

    def _necessary_condition_exercise(self, pair: dict) -> dict:
        a, b = pair["title_a"], pair["title_b"]
        question = (
            f"Según el pasaje de tus apuntes, no puede haber {b} sin {a}: "
            f"{a} es condición necesaria para {b}. "
            f"¿Cuál enunciado lógico expresa correctamente esa dependencia?"
        )
        options = [
            {
                "id": "IMPLIES_BA",
                "label": f"Si hay {b}, necesariamente hubo {a} antes («si {b}, entonces {a}»)",
                "correct": True,
            },
            {
                "id": "IMPLIES_AB",
                "label": f"Si hay {a}, entonces hay {b} («si {a}, entonces {b}»)",
            },
            {
                "id": "AND",
                "label": f"{a} y {b} deben darse siempre al mismo tiempo",
            },
            {
                "id": "OR",
                "label": f"Basta {a} o {b}, no importa cuál",
            },
        ]
        explanation = (
            f"Si {a} es necesaria para {b}, no puede existir {b} sin {a}. "
            f"En lógica: {b} → {a} («si hay {b}, entonces hay {a}»)."
        )
        return self._base_exercise(pair, "necessary", question, options, explanation)

    def _sufficient_condition_exercise(self, pair: dict) -> dict:
        a, b = pair["title_a"], pair["title_b"]
        question = (
            f"El apunte indica que {a} basta por sí sola para producir {b}: "
            f"{a} es condición suficiente para {b}. "
            f"¿Cómo se formula eso en lógica proposicional?"
        )
        options = [
            {
                "id": "IMPLIES_AB",
                "label": f"Si se cumple {a}, entonces se cumple {b} («si {a}, entonces {b}»)",
                "correct": True,
            },
            {
                "id": "IMPLIES_BA",
                "label": f"Si se cumple {b}, entonces se cumple {a}",
            },
            {
                "id": "IFF",
                "label": f"{a} y {b} son equivalentes: uno implica al otro y viceversa",
            },
            {
                "id": "OR",
                "label": f"Con {a} o con {b} basta, da lo mismo cuál",
            },
        ]
        explanation = (
            f"Condición suficiente: alcanza {a} para que ocurra {b}. "
            f"Forma lógica: {a} → {b}."
        )
        return self._base_exercise(pair, "sufficient", question, options, explanation)

    def _conjunction_truth_exercise(self, pair: dict) -> dict:
        a, b = pair["title_a"], pair["title_b"]
        question = (
            f"Pensemos en proposiciones sobre {a} y {b}. "
            f"Si en un caso concreto sabemos que «{a} es cierto» y «{b} es falso», "
            f"¿es verdadero el enunciado «{a} y {b}» (ambos a la vez)?"
        )
        options = [
            {
                "id": "false",
                "label": "No: la conjunción exige que las dos proposiciones sean verdaderas",
                "correct": True,
            },
            {
                "id": "true",
                "label": "Sí: basta con que una de las dos sea verdadera",
            },
        ]
        explanation = (
            f"En una conjunción ({a} ∧ {b}), si una proposición es falsa, "
            f"el conjunto completo es falso. Verdadero ∧ Falso = Falso."
        )
        return self._base_exercise(pair, "truth", question, options, explanation)

    def _negation_exercise(self, pair: dict) -> dict:
        a, b = pair["title_a"], pair["title_b"]
        question = (
            f"Un compañero afirma: «Se cumplen {a} y {b} al mismo tiempo». "
            f"Tú sabes que eso es falso. "
            f"¿Cuál es la negación lógica correcta de «{a} y {b}»?"
        )
        options = [
            {
                "id": "NOT_A_OR_NOT_B",
                "label": f"No se cumple {a}, o no se cumple {b}, o ninguna de las dos (¬{a} o ¬{b})",
                "correct": True,
            },
            {
                "id": "NOT_A_AND_NOT_B",
                "label": f"Ninguna se cumple: ni {a} ni {b} (¬{a} y ¬{b})",
            },
            {
                "id": "NOT_A",
                "label": f"Solo se niega {a}, pero {b} puede cumplirse",
            },
            {
                "id": "IMPLIES_AB",
                "label": f"Si hay {a}, entonces hay {b}",
            },
        ]
        explanation = (
            f"Por De Morgan, negar «{a} y {b}» es «no {a} o no {b}» (¬({a} ∧ {b}) ≡ ¬{a} ∨ ¬{b}). "
            f"Basta que falle una para que la conjunción sea falsa."
        )
        return self._base_exercise(pair, "negation", question, options, explanation)

    def _biconditional_exercise(self, pair: dict) -> dict:
        a, b = pair["title_a"], pair["title_b"]
        question = (
            f"En el fragmento de apuntes, {a} y {b} parecen definirse mutuamente: "
            f"no hay uno sin el otro, y viceversa. "
            f"¿Qué operador expresa esa relación de «si y solo si»?"
        )
        options = [
            {
                "id": "IFF",
                "label": f"{a} implica {b} y {b} implica {a}: se dan «si y solo si» (bicondicional)",
                "correct": True,
            },
            {
                "id": "IMPLIES_AB",
                "label": f"Solo {a} implica {b}, pero no al revés",
            },
            {
                "id": "AND",
                "label": f"Simplemente ocurren juntos en el mismo párrafo, sin relación lógica",
            },
            {
                "id": "OR",
                "label": f"Puede haber {a} o {b} indistintamente",
            },
        ]
        explanation = (
            f"La bicondicional ({a} ↔ {b}) significa que cada uno es condición "
            f"necesaria y suficiente del otro: «{a} si y solo si {b}»."
        )
        return self._base_exercise(pair, "biconditional", question, options, explanation)

    def _fallback_exercises(self, count: int) -> list[dict]:
        generic = [
            {
                "id_a": "0",
                "title_a": "Oferta",
                "title_b": "Aceptación",
                "id_b": "1",
                "context": (
                    "En doctrina civil, la formación del contrato exige concurrencia "
                    "de una proposión (oferta) y una manifestación de voluntad coincidente (aceptación)."
                ),
            },
            {
                "id_a": "2",
                "title_a": "Retractación tempestiva",
                "title_b": "Aceptación",
                "id_b": "3",
                "context": (
                    "La retractación tempestiva es aquella que se produce antes de la "
                    "aceptación de la oferta, cuando aún no ha nacido el contrato."
                ),
            },
            {
                "id_a": "4",
                "title_a": "Obligación",
                "title_b": "Derecho personal",
                "id_b": "5",
                "context": (
                    "Toda obligación correlaciona un deber de dar, hacer o no hacer "
                    "con un derecho personal exigible para el acreedor."
                ),
            },
        ]
        builders = [
            self._conjunction_exercise,
            self._necessary_condition_exercise,
            self._sufficient_condition_exercise,
            self._negation_exercise,
        ]
        exercises = []
        for i, pair in enumerate(generic):
            if len(exercises) >= count:
                break
            exercises.append(builders[i % len(builders)](pair))
        return exercises

    @staticmethod
    def check_answer(correct: str, given: str) -> bool:
        return correct.strip().upper() == given.strip().upper()
