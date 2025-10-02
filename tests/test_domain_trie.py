import unittest

from dedupe.domainTrie import DomainTrie

class DomainTrieTests(unittest.TestCase):
    def setUp(self):
        self.trie = DomainTrie()

    def test_add_and_contains_exact_domain(self):
        self.assertTrue(self.trie.add("example.com"))
        self.assertTrue(self.trie.contains("example.com"))
        self.assertFalse(self.trie.contains("foo.example.com"))

    def test_wildcard_covers_subdomains(self):
        self.assertTrue(self.trie.add("*.example.com"))
        self.assertTrue(self.trie.contains("foo.example.com"))
        self.assertFalse(self.trie.contains("bar.foo.example.com"))  # nested, not covered
        self.assertFalse(self.trie.contains("example.com"))

    def test_wildcard_removes_existing_subdomains(self):
        self.assertTrue(self.trie.add("foo.example.com"))
        self.assertTrue(self.trie.add("bar.example.com"))
        self.assertTrue(self.trie.contains("foo.example.com"))
        self.assertTrue(self.trie.contains("bar.example.com"))

        # Adding wildcard should remove more specific entries, but cover them logically
        self.assertTrue(self.trie.add("*.example.com"))
        self.assertTrue(self.trie.contains("foo.example.com"))
        self.assertTrue(self.trie.contains("bar.example.com"))

        # Attempting to add more specific entries should now be a no-op
        self.assertFalse(self.trie.add("baz.example.com"))
        self.assertTrue(self.trie.contains("baz.example.com"))
        
        # But nested subdomains are NOT covered
        self.assertFalse(self.trie.contains("deep.baz.example.com"))

    def test_apex_and_wildcard_interaction(self):
        # Adding wildcard clears apex if it was added first
        self.assertTrue(self.trie.add("example.com"))
        self.assertTrue(self.trie.add("*.example.com"))
        self.assertFalse(self.trie.contains("example.com"))  # cleared by wildcard
        self.assertTrue(self.trie.contains("foo.example.com"))
        
        # But apex can be added after wildcard
        self.trie = DomainTrie()
        self.assertTrue(self.trie.add("*.example.com"))
        self.assertTrue(self.trie.add("example.com"))
        self.assertTrue(self.trie.contains("example.com"))
        self.assertTrue(self.trie.contains("foo.example.com"))

    def test_normalization(self):
        # Test case-insensitivity and trailing dot handling
        self.assertTrue(self.trie.add("Example.COM"))
        self.assertTrue(self.trie.contains("example.com"))
        self.assertTrue(self.trie.contains("EXAMPLE.COM."))

    def test_multiple_wildcards_at_different_levels(self):
        # More specific wildcard first, then broader
        self.assertTrue(self.trie.add("*.foo.example.com"))
        self.assertTrue(self.trie.add("*.bar.example.com"))
        self.assertTrue(self.trie.contains("baz.foo.example.com"))
        self.assertTrue(self.trie.contains("qux.bar.example.com"))
        self.assertFalse(self.trie.contains("foo.example.com"))
        self.assertFalse(self.trie.contains("bar.example.com"))
        
        # Broader wildcard can be added at a different level
        self.assertTrue(self.trie.add("*.example.com"))
        self.assertTrue(self.trie.contains("anything.example.com"))

    def test_len_and_iteration(self):
        self.trie.add("example.com")
        self.trie.add("foo.example.com")
        self.trie.add("*.test.com")
        self.assertEqual(len(self.trie), 3)
        domains = sorted(list(self.trie.iter_domains()))
        self.assertIn("example.com", domains)
        self.assertIn("foo.example.com", domains)
        self.assertIn("*.test.com", domains)
        self.assertEqual(len(domains), 3)

    def test_deep_nesting(self):
        self.assertTrue(self.trie.add("a.b.c.d.e.f.g.com"))
        self.assertTrue(self.trie.contains("a.b.c.d.e.f.g.com"))
        self.assertFalse(self.trie.contains("b.c.d.e.f.g.com"))

    def test_wildcard_only_one_level_deep(self):
        # Wildcard matches exactly one additional label
        self.assertTrue(self.trie.add("*.example.com"))
        self.assertTrue(self.trie.contains("a.example.com"))
        self.assertTrue(self.trie.contains("b.example.com"))
        self.assertFalse(self.trie.contains("a.b.example.com"))
        self.assertFalse(self.trie.contains("x.y.z.example.com"))
        
        # Can add wildcard at a nested level
        self.trie = DomainTrie()  # Fresh trie to avoid conflict
        self.assertTrue(self.trie.add("*.foo.example.com"))
        self.assertTrue(self.trie.contains("bar.foo.example.com"))
        self.assertFalse(self.trie.contains("baz.bar.foo.example.com"))

    def test_remove_concrete_domain(self):
        self.assertTrue(self.trie.add("example.com"))
        self.assertTrue(self.trie.add("foo.example.com"))
        self.assertTrue(self.trie.contains("example.com"))
        self.assertTrue(self.trie.contains("foo.example.com"))
        
        # Remove concrete domain
        self.assertTrue(self.trie.remove("example.com"))
        self.assertFalse(self.trie.contains("example.com"))
        self.assertTrue(self.trie.contains("foo.example.com"))  # Other domain unaffected
        
        # Try removing again - should return False
        self.assertFalse(self.trie.remove("example.com"))

    def test_remove_wildcard(self):
        self.assertTrue(self.trie.add("*.example.com"))
        self.assertTrue(self.trie.contains("foo.example.com"))
        
        # Remove wildcard
        self.assertTrue(self.trie.remove("*.example.com"))
        self.assertFalse(self.trie.contains("foo.example.com"))
        
        # Try removing again - should return False
        self.assertFalse(self.trie.remove("*.example.com"))

    def test_remove_nonexistent_domain(self):
        self.assertTrue(self.trie.add("example.com"))
        self.assertFalse(self.trie.remove("foo.example.com"))  # Never added
        self.assertFalse(self.trie.remove("other.com"))  # Never added

    def test_remove_cleans_up_empty_nodes(self):
        # Add nested domains
        self.assertTrue(self.trie.add("a.b.c.example.com"))
        self.assertTrue(self.trie.add("x.b.c.example.com"))
        self.assertEqual(len(self.trie), 2)
        
        # Remove one - shared path should remain
        self.assertTrue(self.trie.remove("a.b.c.example.com"))
        self.assertEqual(len(self.trie), 1)
        self.assertTrue(self.trie.contains("x.b.c.example.com"))
        
        # Remove the other - entire path should be cleaned
        self.assertTrue(self.trie.remove("x.b.c.example.com"))
        self.assertEqual(len(self.trie), 0)

    def test_remove_with_normalization(self):
        self.assertTrue(self.trie.add("Example.COM"))
        self.assertTrue(self.trie.contains("example.com"))
        
        # Remove using different case
        self.assertTrue(self.trie.remove("EXAMPLE.com."))
        self.assertFalse(self.trie.contains("example.com"))

    def test_remove_does_not_affect_wildcards(self):
        self.assertTrue(self.trie.add("*.example.com"))
        self.assertTrue(self.trie.add("example.com"))
        
        # Removing concrete domain shouldn't affect wildcard
        self.assertTrue(self.trie.remove("example.com"))
        self.assertTrue(self.trie.contains("foo.example.com"))  # Wildcard still works


if __name__ == "__main__":
    unittest.main()
