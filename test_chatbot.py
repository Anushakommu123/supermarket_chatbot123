"""Run all tests with: python -m unittest -v"""
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from chatbot import SupermarketChatbot, DatasetError, final_price, load_products


class ChatbotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = SupermarketChatbot()

    def test_available(self):
        self.assertIn("Milk is available", self.bot.reply("Is milk available?"))

    def test_out_of_stock(self):
        self.assertIn("Butter is currently out of stock", self.bot.reply("Do you have butter?"))

    def test_unknown(self):
        self.assertIn("could not find", self.bot.reply("Do you have dragonfruit?"))

    def test_price(self):
        self.assertIn("₹30", self.bot.reply("How much does milk cost?"))

    def test_discount_calculation(self):
        rice = next(p for p in self.bot.products if p['product_name'] == 'Rice')
        self.assertEqual(final_price(rice), Decimal('90.00'))
        self.assertIn("₹90.00", self.bot.reply("price of rice"))

    def test_general_offers(self):
        reply = self.bot.reply("Are there any discounts?")
        self.assertIn("Rice", reply)
        self.assertIn("Shampoo", reply)

    def test_category_offers(self):
        reply = self.bot.reply("Show me dairy products with discounts")
        self.assertIn("Cheese", reply)
        self.assertNotIn("Rice", reply)

    def test_offers_available_only(self):
        reply = self.bot.reply("products on sale")
        for p in self.bot.products:
            if not p['stock'] or not p['discount']:
                self.assertNotIn('**' + p['product_name'] + '**', reply)

    def test_alternatives(self):
        context = {}
        self.bot.reply("Is butter available?", context)
        reply = self.bot.reply("Show me alternatives", context)
        self.assertIn("Milk", reply)
        self.assertNotIn("**Butter**", reply)

    def test_category(self):
        reply = self.bot.reply("Show me fruits")
        self.assertIn("Banana", reply)
        self.assertNotIn("**Apple**", reply)

    def test_budget(self):
        reply = self.bot.reply("Show me snacks under ₹100")
        self.assertIn("Chocolate", reply)  # Original 100, selling price 85.
        self.assertNotIn("Popcorn", reply)
        self.assertNotIn("Milk", reply)
        self.assertIn("Rice", self.bot.reply("between 50 and 200 rupees"))
        self.assertNotIn("**Orange**", self.bot.reply("below 50 rupees"))

    def test_followup(self):
        context = {}
        self.bot.reply("milk", context)
        self.assertIn("₹30", self.bot.reply("What is its price?", context))
        self.assertIn("no discount on Milk", self.bot.reply("Is there any discount on it?", context))

    def test_switching(self):
        context = {}
        self.bot.reply("milk", context)
        self.assertIn("Rice", self.bot.reply("price of rice", context))
        self.assertEqual(context['product'], 'Rice')
        self.bot.reply("Show me snacks", context)
        self.assertIsNone(context['product'])
        self.assertIn("Shampoo", self.bot.reply("Any discounted products?", context))
        self.assertNotIn("Rice", self.bot.reply("discounts on dairy", context))

    def test_case(self):
        self.assertIn("Milk is available", self.bot.reply("IS MILK AVAILABLE!!!"))

    def test_overlap(self):
        context = {}
        reply = self.bot.reply("price of orange juice", context)
        self.assertIn("Orange Juice", reply)
        self.assertEqual(context['product'], 'Orange Juice')
        self.assertIn("₹90", reply)

    def test_empty(self):
        self.assertIn("Please enter", self.bot.reply("  "))

    def test_unrelated(self):
        self.assertIn("supermarket", self.bot.reply("Who won the cricket match?"))

    def test_missing_file(self):
        with self.assertRaises(DatasetError):
            load_products(Path('missing-file.csv'))

    def test_invalid_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.csv'
            path.write_text('name,price\nMilk,30\n')
            with self.assertRaises(DatasetError):
                load_products(path)
            for value in ('-1', 'NaN', 'inf', 'invalid'):
                path.write_text('product_id,product_name,category,price,stock,discount,unit\n'
                                f'1,Milk,Dairy,{value},5,0,500 ml\n')
                with self.assertRaises(DatasetError):
                    load_products(path)

    def test_typo_and_plural(self):
        self.assertIn("Milk is available", self.bot.reply("Is milkk available?"))
        self.assertIn("Orange is available", self.bot.reply("Do you have oranges?"))

    def test_ambiguous(self):
        self.assertIn("one product", self.bot.reply("milk and rice"))
        self.assertIn("Which product", self.bot.reply("What is its price?", {}))
        self.assertIn("Which product", self.bot.reply("Do you have juice?"))

    def test_unknown_discount(self):
        self.assertIn("could not find", self.bot.reply("discount on dragonfruit"))

    def test_budget_boundaries(self):
        self.assertNotIn("**Orange**", self.bot.reply("products under 80"))
        self.assertIn("**Orange**", self.bot.reply("products between 80 and 80"))

    def test_stock_and_discount_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.csv'
            for stock, discount in ((-1, 0), (1.5, 0), (1, 101), (1, -5)):
                path.write_text('product_id,product_name,category,price,stock,discount,unit\n'
                                f'1,Milk,Dairy,30,{stock},{discount},500 ml\n')
                with self.assertRaises(DatasetError):
                    load_products(path)

    def test_dataset_coverage(self):
        self.assertGreaterEqual(len(self.bot.products), 50)
        self.assertEqual(len(self.bot.categories), 8)


class FrontendTests(unittest.TestCase):
    def test_chat_actions_and_clear(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=30)
        self.assertFalse(app.exception)
        app.chat_input[0].set_value('Is milk available?').run()
        self.assertEqual(app.session_state['context']['product'], 'Milk')
        app.chat_input[0].set_value('What is its price?').run()
        self.assertIn('₹30', app.session_state['messages'][-1]['content'])
        for label in ('Check Availability', "Today's Offers", 'Browse Categories', 'Products Under ₹100'):
            next(button for button in app.button if button.label == label).click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['messages'][-1]['role'], 'assistant')
        next(button for button in app.button if button.label == 'Clear Chat').click().run()
        self.assertEqual(app.session_state['context'], {})
        self.assertEqual(len(app.session_state['messages']), 1)


if __name__ == '__main__':
    unittest.main()
