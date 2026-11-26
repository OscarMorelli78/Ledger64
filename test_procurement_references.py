import unittest
from procurement_references import reference_check
from test_procurement import order,invoice,delivery,inputs

class ReferenceTests(unittest.TestCase):
    def test_exact_reference(self):
        r=reference_check(invoice("I","50","450"),inputs(order()))
        self.assertEqual(r["status"],"REFERENCES_COMPATIBLE")
        self.assertEqual(len(r["lines"][0]["order_source_sha256"]),64)
    def test_wrong_supplier(self):
        doc=invoice("I","50","450");doc["supplier"]="OTHER"
        self.assertEqual(reference_check(doc,inputs(order()))["lines"][0]["status"],"ORDER_NOT_FOUND")
    def test_wrong_sku(self):
        doc=invoice("I","50","450");doc["lines"][0]["sku"]="OTHER"
        self.assertEqual(reference_check(doc,inputs(order()))["lines"][0]["status"],"REFERENCE_CONFLICT")
    def test_wrong_order_line(self):
        doc=invoice("I","50","450");doc["lines"][0]["order_line"]="2"
        self.assertEqual(reference_check(doc,inputs(order()))["lines"][0]["status"],"ORDER_NOT_FOUND")
    def test_before_order(self):
        doc=delivery("R","50");doc["date"]="2025-12-01"
        self.assertEqual(reference_check(doc,inputs(order()))["lines"][0]["status"],"REFERENCE_CONFLICT")
    def test_order_not_applicable(self):
        self.assertEqual(reference_check(order(),[])["status"],"NOT_APPLICABLE")
if __name__=="__main__":unittest.main()
