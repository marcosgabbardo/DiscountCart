"""
Category service for automatic product categorization using Anthropic API.

This service categorizes products into granular categories that represent
the generic product type (without brand), enabling direct price comparison
between similar products from different stores/brands.

Example categorizations:
- "Leite Italac UHT 1L" → "Leite UHT 1L"
- "Coração de Frango Sadia 1kg" → "Coração de Frango"
- "Requeijão Vigor 200g" → "Requeijão"
- "YoPro Morango 250ml" → "Bebida Láctea"
- "Kefir Natural 170g" → "Iogurte"
- "Água de Coco Sococo 1L" → "Água de Coco"
"""

from typing import Optional, List
import anthropic

from config import settings
from database import get_db


# Example categories to guide the AI (not a fixed list)
CATEGORY_EXAMPLES = [
    # Laticínios
    "Leite UHT Integral",
    "Leite UHT Desnatado",
    "Leite UHT Semidesnatado",
    "Leite em Pó",
    "Leite Condensado",
    "Creme de Leite",
    "Queijo Mussarela",
    "Queijo Prato",
    "Queijo Parmesão",
    "Queijo Coalho",
    "Queijo Minas",
    "Requeijão",
    "Requeijão Light",
    "Cream Cheese",
    "Iogurte Natural",
    "Iogurte Grego",
    "Iogurte com Frutas",
    "Bebida Láctea",
    "Kefir",
    "Manteiga com Sal",
    "Manteiga sem Sal",
    "Margarina",

    # Ovos
    "Ovos Brancos",
    "Ovos Vermelhos",
    "Ovos Caipira",
    "Ovos Orgânicos",

    # Carnes - Frango (granular)
    "Peito de Frango",
    "Coxa de Frango",
    "Sobrecoxa de Frango",
    "Asa de Frango",
    "Coração de Frango",
    "Moela de Frango",
    "Fígado de Frango",
    "Frango Inteiro",
    "Filé de Frango",
    "Coxinha da Asa",

    # Carnes - Bovina (granular)
    "Picanha",
    "Alcatra",
    "Maminha",
    "Fraldinha",
    "Costela Bovina",
    "Acém",
    "Patinho",
    "Coxão Mole",
    "Coxão Duro",
    "Músculo",
    "Cupim",
    "Carne Moída",
    "Filé Mignon",
    "Contrafilé",

    # Carnes - Suína (granular)
    "Pernil Suíno",
    "Lombo Suíno",
    "Costela Suína",
    "Bisteca Suína",
    "Bacon",
    "Panceta",

    # Embutidos
    "Linguiça Calabresa",
    "Linguiça Toscana",
    "Salsicha",
    "Presunto",
    "Mortadela",
    "Salame",
    "Peito de Peru",

    # Peixes e Frutos do Mar
    "Filé de Tilápia",
    "Filé de Salmão",
    "Camarão",
    "Sardinha",
    "Atum em Lata",
    "Bacalhau",

    # Grãos e Cereais
    "Arroz Branco",
    "Arroz Integral",
    "Arroz Parboilizado",
    "Feijão Carioca",
    "Feijão Preto",
    "Feijão Fradinho",
    "Lentilha",
    "Grão de Bico",

    # Massas
    "Macarrão Espaguete",
    "Macarrão Penne",
    "Macarrão Parafuso",
    "Macarrão Integral",
    "Lasanha",

    # Farinhas
    "Farinha de Trigo",
    "Farinha de Mandioca",
    "Farinha de Rosca",
    "Farinha de Aveia",
    "Fubá",

    # Açúcar e Adoçantes
    "Açúcar Refinado",
    "Açúcar Cristal",
    "Açúcar Mascavo",
    "Açúcar Demerara",
    "Adoçante",

    # Café e Chás
    "Café em Pó",
    "Café Solúvel",
    "Café em Cápsulas",
    "Chá de Camomila",
    "Chá Verde",
    "Chá Mate",

    # Óleos e Azeites
    "Óleo de Soja",
    "Óleo de Canola",
    "Óleo de Girassol",
    "Azeite de Oliva Extra Virgem",
    "Azeite de Oliva",

    # Bebidas
    "Água Mineral",
    "Água de Coco",
    "Refrigerante Cola",
    "Refrigerante Guaraná",
    "Refrigerante Laranja",
    "Suco de Laranja",
    "Suco de Uva",
    "Suco em Pó",
    "Cerveja Pilsen",
    "Cerveja Lager",
    "Vinho Tinto",
    "Vinho Branco",

    # Frutas Secas e Castanhas
    "Castanha de Caju",
    "Castanha do Pará",
    "Amendoim",
    "Amêndoas",
    "Nozes",
    "Mix de Castanhas",
    "Uva Passa",
    "Damasco Seco",

    # Pães e Padaria
    "Pão de Forma",
    "Pão de Forma Integral",
    "Pão Francês",
    "Pão de Hot Dog",
    "Pão de Hambúrguer",
    "Torrada",
    "Bisnaguinha",

    # Biscoitos e Snacks
    "Biscoito Cream Cracker",
    "Biscoito Água e Sal",
    "Biscoito Recheado",
    "Biscoito Integral",
    "Bolacha Maria",
    "Salgadinho",

    # Molhos e Condimentos
    "Molho de Tomate",
    "Extrato de Tomate",
    "Ketchup",
    "Mostarda",
    "Maionese",
    "Molho de Soja",
    "Vinagre",
    "Sal Refinado",
    "Sal Grosso",

    # Higiene e Limpeza
    "Sabonete",
    "Shampoo",
    "Condicionador",
    "Pasta de Dente",
    "Papel Higiênico",
    "Papel Toalha",
    "Detergente",
    "Sabão em Pó",
    "Amaciante",
    "Desinfetante",
    "Água Sanitária",
]


class CategoryService:
    """Service for categorizing products using Anthropic API."""

    def __init__(self):
        self.db = get_db()
        self.api_key = settings.ANTHROPIC_API_KEY
        self._client = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY não configurada. "
                    "Adicione sua chave no arquivo .env"
                )
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def categorize_product(self, product_title: str) -> str:
        """
        Categorize a product based on its title using Anthropic API.

        The category should be the generic product name (without brand),
        allowing direct comparison between similar products.

        Args:
            product_title: The product title to categorize

        Returns:
            The category name (generic product type)
        """
        examples = "\n".join(f"  - {cat}" for cat in CATEGORY_EXAMPLES[:50])

        prompt = f"""Você é um especialista em categorização de produtos de supermercado brasileiro.

Sua tarefa é extrair o NOME GENÉRICO DO PRODUTO (sem marca) a partir do título.
O objetivo é permitir comparação de preços entre produtos equivalentes de diferentes marcas/lojas.

REGRAS IMPORTANTES:
1. Remova SEMPRE a marca do produto (Italac, Sadia, Perdigão, Vigor, Nestlé, etc.)
2. Mantenha características importantes: tipo (integral, desnatado), corte de carne, tamanho quando relevante
3. Use categorias GRANULARES e ESPECÍFICAS (ex: "Coração de Frango", não "Frango")
4. Para bebidas lácteas como YoPro, Danone Protein, etc., use "Bebida Láctea"
5. Kefir deve ser categorizado como "Iogurte" ou "Kefir" (prefira Kefir se for kefir mesmo)
6. Água de coco deve ser "Água de Coco" (categoria específica)
7. Castanhas devem ter categoria própria: "Castanha de Caju", "Castanha do Pará", etc.
8. Para cortes de carne, seja específico: "Picanha", "Coração de Frango", "Filé de Tilápia"
9. Responda APENAS com o nome da categoria, sem explicações

EXEMPLOS de categorias:
{examples}

EXEMPLOS de categorização:
- "Leite Italac UHT Integral 1L" → "Leite UHT Integral"
- "Leite Piracanjuba Desnatado 1L" → "Leite UHT Desnatado"
- "Coração de Frango Sadia Congelado 1kg" → "Coração de Frango"
- "Peito de Frango Seara Congelado" → "Peito de Frango"
- "Requeijão Vigor Cremoso 200g" → "Requeijão"
- "Requeijão Light Polenghi" → "Requeijão Light"
- "YoPro Morango 250ml" → "Bebida Láctea"
- "Danone Protein Baunilha" → "Bebida Láctea"
- "Kefir Natural Keffy 170g" → "Kefir"
- "Água de Coco Sococo 1L" → "Água de Coco"
- "Castanha de Caju Torrada 100g" → "Castanha de Caju"
- "Picanha Bovina Resfriada kg" → "Picanha"
- "Filé de Tilápia Congelado" → "Filé de Tilápia"
- "Café Pilão Tradicional 500g" → "Café em Pó"
- "Nescafé Dolce Gusto Cappuccino" → "Café em Cápsulas"

Produto: {product_title}

Categoria:"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            category = message.content[0].text.strip()

            # Clean up the response - remove quotes and extra whitespace
            category = category.strip('"\'').strip()

            # Ensure we have a valid category
            if not category or len(category) < 2:
                return "Outros"

            return category

        except anthropic.APIError as e:
            print(f"Erro na API Anthropic: {e}")
            return "Outros"

    def update_product_category(self, product_id: int, category: str) -> bool:
        """
        Update the category for a product in the database.

        Args:
            product_id: The product ID
            category: The category to set

        Returns:
            True if successful
        """
        query = "UPDATE products SET category = %s WHERE id = %s"
        self.db.execute_query(query, (category, product_id), fetch=False)
        return True

    def categorize_and_save(self, product_id: int, product_title: str) -> str:
        """
        Categorize a product and save the category to the database.

        Args:
            product_id: The product ID
            product_title: The product title

        Returns:
            The assigned category
        """
        category = self.categorize_product(product_title)
        self.update_product_category(product_id, category)
        return category

    def recategorize_all(self) -> List[dict]:
        """
        Recategorize ALL products (useful when updating categorization logic).

        Returns:
            List of products that were recategorized
        """
        query = """
            SELECT id, title FROM products
            WHERE title IS NOT NULL AND is_active = TRUE
        """
        results = self.db.execute_query(query)

        categorized = []
        total = len(results)
        for i, row in enumerate(results):
            product_id = row['id']
            title = row['title']

            print(f"[{i+1}/{total}] Categorizando: {title[:50]}...")
            category = self.categorize_and_save(product_id, title)
            print(f"  -> Categoria: {category}")

            categorized.append({
                'id': product_id,
                'title': title,
                'category': category
            })

        return categorized

    def categorize_all_uncategorized(self) -> List[dict]:
        """
        Find and categorize all products without a category.

        Returns:
            List of products that were categorized
        """
        query = """
            SELECT id, title FROM products
            WHERE category IS NULL AND title IS NOT NULL AND is_active = TRUE
        """
        results = self.db.execute_query(query)

        categorized = []
        total = len(results)
        for i, row in enumerate(results):
            product_id = row['id']
            title = row['title']

            print(f"[{i+1}/{total}] Categorizando: {title[:50]}...")
            category = self.categorize_and_save(product_id, title)
            print(f"  -> Categoria: {category}")

            categorized.append({
                'id': product_id,
                'title': title,
                'category': category
            })

        return categorized

    def get_products_by_category(self, category: str) -> List[dict]:
        """
        Get all products in a specific category.

        Args:
            category: The category to filter by

        Returns:
            List of products with their details
        """
        query = """
            SELECT id, asin, title, store, category, current_price, target_price,
                   lowest_price, highest_price, is_active
            FROM products
            WHERE category = %s AND is_active = TRUE
            ORDER BY current_price ASC
        """
        return self.db.execute_query(query, (category,))

    def search_categories(self, search_term: str) -> List[dict]:
        """
        Search for categories containing the search term.

        Args:
            search_term: The term to search for

        Returns:
            List of matching categories with product counts
        """
        query = """
            SELECT
                category,
                COUNT(*) as product_count,
                MIN(current_price) as min_price,
                MAX(current_price) as max_price
            FROM products
            WHERE category LIKE %s AND is_active = TRUE AND current_price IS NOT NULL
            GROUP BY category
            ORDER BY product_count DESC
        """
        return self.db.execute_query(query, (f"%{search_term}%",))

    def get_cheapest_by_category(self, category: str) -> Optional[dict]:
        """
        Get the cheapest product in a category.

        Args:
            category: The category to search

        Returns:
            The cheapest product or None
        """
        query = """
            SELECT id, asin, title, store, category, current_price, target_price
            FROM products
            WHERE category = %s AND is_active = TRUE AND current_price IS NOT NULL
            ORDER BY current_price ASC
            LIMIT 1
        """
        results = self.db.execute_query(query, (category,))
        return results[0] if results else None

    def get_all_categories(self) -> List[dict]:
        """
        Get all categories that have products, with product count and price range.

        Returns:
            List of categories with statistics
        """
        query = """
            SELECT
                category,
                COUNT(*) as product_count,
                MIN(current_price) as min_price,
                MAX(current_price) as max_price,
                AVG(current_price) as avg_price
            FROM products
            WHERE category IS NOT NULL AND is_active = TRUE AND current_price IS NOT NULL
            GROUP BY category
            ORDER BY category
        """
        return self.db.execute_query(query)

    def compare_prices_by_category(self, category: str) -> List[dict]:
        """
        Compare prices of products in the same category across different stores.

        Args:
            category: The category to compare

        Returns:
            List of products sorted by price
        """
        query = """
            SELECT
                p.id,
                p.title,
                p.store,
                p.current_price,
                p.lowest_price,
                p.highest_price,
                (SELECT AVG(ph.price) FROM price_history ph
                 WHERE ph.product_id = p.id
                 AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as avg_30d
            FROM products p
            WHERE p.category = %s AND p.is_active = TRUE AND p.current_price IS NOT NULL
            ORDER BY p.current_price ASC
        """
        return self.db.execute_query(query, (category,))

    @staticmethod
    def get_available_categories() -> List[str]:
        """Return example categories (for reference only, categories are dynamic)."""
        return CATEGORY_EXAMPLES.copy()
