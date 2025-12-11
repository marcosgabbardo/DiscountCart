"""
Category service for automatic product categorization using Anthropic API.
"""

from typing import Optional, List
import anthropic

from config import settings
from database import get_db


# Predefined categories for supermarket products
PRODUCT_CATEGORIES = [
    "Leite",
    "Queijo",
    "Iogurte",
    "Manteiga",
    "Ovos",
    "Pao",
    "Arroz",
    "Feijao",
    "Macarrao",
    "Farinha",
    "Acucar",
    "Cafe",
    "Cha",
    "Oleo",
    "Azeite",
    "Sal",
    "Temperos",
    "Molhos",
    "Enlatados",
    "Conservas",
    "Cereais",
    "Biscoitos",
    "Chocolates",
    "Doces",
    "Sorvete",
    "Refrigerante",
    "Suco",
    "Agua",
    "Cerveja",
    "Vinho",
    "Bebidas Alcoolicas",
    "Carne Bovina",
    "Carne Suina",
    "Frango",
    "Peixe",
    "Frutos do Mar",
    "Embutidos",
    "Frios",
    "Frutas",
    "Verduras",
    "Legumes",
    "Congelados",
    "Higiene Pessoal",
    "Limpeza",
    "Papel",
    "Pet",
    "Bebe",
    "Outros",
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

        Args:
            product_title: The product title to categorize

        Returns:
            The category name
        """
        categories_list = ", ".join(PRODUCT_CATEGORIES)

        prompt = f"""Você é um especialista em categorização de produtos de supermercado.
Dado o nome de um produto, você deve classificá-lo em UMA das categorias disponíveis.

Categorias disponíveis: {categories_list}

Regras:
1. Responda APENAS com o nome exato da categoria, sem explicações adicionais
2. Use a categoria "Outros" apenas se o produto não se encaixar em nenhuma outra categoria
3. Para laticínios como leite, use "Leite"; para queijos, use "Queijo", etc.
4. Para carnes, classifique pelo tipo: "Carne Bovina", "Carne Suina", "Frango", etc.

Produto: {product_title}

Categoria:"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=50,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            category = message.content[0].text.strip()

            # Validate the category is in our list
            if category in PRODUCT_CATEGORIES:
                return category

            # Try to find a close match
            category_lower = category.lower()
            for valid_category in PRODUCT_CATEGORIES:
                if valid_category.lower() == category_lower:
                    return valid_category

            # Default to "Outros" if not found
            return "Outros"

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
        for row in results:
            product_id = row['id']
            title = row['title']

            print(f"Categorizando: {title[:50]}...")
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
        """Return the list of available product categories."""
        return PRODUCT_CATEGORIES.copy()
