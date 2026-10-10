"""1xtnr: calls preserve callable identity, receiver evidence and callee syntax."""
from __future__ import annotations
import collections
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from test_graph_incremental_merge import _RepoDriver, _edge_keys, load_graph_indexer, load_index_state_store
import sqlite3
import tempfile


# Grammar-valid fixtures captured on builder51 before this repair.
PROFILE_FIXTURES = {'java': ('Probe.java',
          'class Probe { Object[] children; Object authenticatedUser; Object getValue() { return null; } '
          'void helper() {} void run(Object b) { helper(); children[0].getValue(); '
          'b.subject().authenticatedUser(); } }'),
 'php': ('probe.php',
         '<?php class Probe { public $children; function helper() {} function getValue() {} function '
         'run($b,$e) { $this->helper(); $this->children[0]->getValue(); $b->subject()->authenticatedUser(); '
         '$e->getKey(); A::stat(); } }'),
 'swift': ('probe.swift',
           'func helper() {}\n'
           'func run(b: AnyObject, children: [AnyObject]) { helper(); children[0].getValue(); '
           'b.subject().authenticatedUser() }'),
 'scala': ('probe.scala',
           'class Probe { val children = Array.empty[Probe]; def helper() = 1; def getValue() = 1; def '
           'run(b: Probe) = { helper(); children(0).getValue(); b.subject().authenticatedUser() } }'),
 'typescript': ('probe.ts',
                'function helper() {} function run(b: any, children: any, foo: any, x: any) { helper(); '
                'b.subject().authenticatedUser(); children[0].getValue(); foo?.bar(); x!.y(); C.m(); }'),
 'javascript': ('probe.js',
                'function helper() {} function run(b, children, foo) { helper(); '
                'b.subject().authenticatedUser(); children[0].getValue(); foo?.bar(); C.m(); }'),
 'go': ('probe.go',
        'package probe\n'
        'func helper() {}\n'
        'func run(b Thing, children []Thing) { helper(); b.subject().authenticatedUser(); '
        'children[0].getValue(); pkg.Fn() }'),
 'rust': ('probe.rs',
          'fn helper() {} fn run(b: Thing, children: Vec<Thing>) { helper(); '
          'b.subject().authenticatedUser(); children[0].getValue(); a::b::c(); }'),
 'c': ('probe.c',
       'void helper(void) {} void run(Thing b, Thing *e, Thing *children) { helper(); '
       'b.subject().authenticatedUser(); children[0].getValue(); e->getKey(); }'),
 'cpp': ('probe.cpp',
         'void helper() {} void run(Thing b, Thing *e, Thing *children) { helper(); '
         'b.subject().authenticatedUser(); children[0].getValue(); e->getKey(); ns::fn(); }'),
 'csharp': ('probe.cs',
            'class Probe { void helper() {} void run(dynamic b, dynamic[] children, dynamic x) { helper(); '
            'b.subject().authenticatedUser(); children[0].getValue(); x?.Y(); Cls.Method(); } }'),
 'kotlin': ('probe.kt',
            'fun helper() {}\n'
            'fun run(b: Thing, children: Array<Thing>) { helper(); children[0].getValue(); '
            'b.subject().authenticatedUser() }'),
 'ruby': ('probe.rb',
          'def helper; end\n'
          'def run(b, children)\n'
          ' helper()\n'
          ' children[0].getValue()\n'
          ' b.subject().authenticatedUser()\n'
          'end\n'),
 'objc': ('probe.m',
          'void helper(void) {} void run(id b, id *children) { helper(); [children[0] getValue]; [[b '
          'subject] authenticatedUser]; }'),
 'bash': ('probe.sh', 'helper() { echo ok; }\nrun() { helper; }\nrun\n')}


def walk(node):
    yield node
    for child in node.named_children:
        yield from walk(child)


class CallIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = load_graph_indexer()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.driver = _RepoDriver(self.g, self.root)

    def build(self, files):
        for path, src in files.items():
            self.driver.write(path, src)
        return self.driver.build_incremental(set(files))

    def artifact(self, lang, src, path=None):
        tree = self.g._ts_parse(lang, src)
        self.assertIsNotNone(tree, f'{lang} grammar required')
        self.assertFalse(tree.root_node.has_error, str(tree.root_node))
        session = object.__new__(self.g.GraphIndexSession)
        session.layer = 'project'
        session.root = self.root
        return session._extract_tree_sitter_artifact(path or ('Fixture.' + lang), src, lang)

    def _call_candidates(self, lang, src):
        tree = self.g._ts_parse(lang, src)
        self.assertIsNotNone(tree, f'{lang} grammar required')
        self.assertFalse(tree.root_node.has_error, str(tree.root_node))
        profile = self.g._TS_LANGUAGE_PROFILES[lang]
        return [(src[n.start_byte:n.end_byte], self.g._ts_relation_candidates(n, src.encode(), 'call', profile.mode, profile))
                for n in walk(tree.root_node) if n.type in profile.call_node_types]

    def test_pure_path_literals_and_positional_controls(self):
        cases = {
            'typescript': ('C.m();', [['C.m']]),
            'cpp': ('void run() { ns::fn(); }', [['ns::fn']]),
            'rust': ('fn run() { a::b::c(); }', [['a::b::c']]),
            'csharp': ('class Probe { void run() { Cls.Method(); } }', [['Cls.Method']]),
            'go': ('package probe\nfunc run() { pkg.Fn() }', [['pkg.Fn']]),
            'php': ('<?php A::stat();', [['stat']]),
            'java': ('class Probe { void run() { Cls.method(); } }', [['method']]),
            'swift': ('helper(); e.getKey()', [['helper'], ['getKey']]),
            'kotlin': ('fun run() { helper(); e.getKey() }', [['helper'], ['getKey']]),
        }
        for lang, (src, expected) in cases.items():
            with self.subTest(lang=lang):
                self.assertEqual([c for _, c in self._call_candidates(lang, src)], expected)

    def test_complex_callee_leaf_matrix(self):
        cases = {
            'typescript': 'function run(b: any, children: any, foo: any, x: any) { b.subject().authenticatedUser(); children[0].getValue(); foo?.bar(); x!.y(); }',
            'javascript': 'function run(b, children, foo) { b.subject().authenticatedUser(); children[0].getValue(); foo?.bar(); }',
            'go': 'package probe\nfunc run(b Thing, children []Thing) { b.subject().authenticatedUser(); children[0].getValue() }',
            'rust': 'fn run(b: Thing, children: Vec<Thing>) { b.subject().authenticatedUser(); children[0].getValue(); }',
            'scala': 'class Probe { def run(b: Probe, children: Array[Probe]) = { b.subject().authenticatedUser(); children(0).getValue() } }',
            'csharp': 'class Probe { void run(dynamic b, dynamic[] children, dynamic x) { b.subject().authenticatedUser(); children[0].getValue(); x?.Y(); } }',
            'c': 'void run(Thing b, Thing *children, Thing *e) { b.subject().authenticatedUser(); children[0].getValue(); e->getKey(); }',
            'cpp': 'void run(Thing b, Thing *children, Thing *e) { b.subject().authenticatedUser(); children[0].getValue(); e->getKey(); }',
            'php': '<?php function run($b,$children,$e) { $b->subject()->authenticatedUser(); $children[0]->getValue(); $e->getKey(); }',
        }
        for lang, src in cases.items():
            with self.subTest(lang=lang):
                rows = self._call_candidates(lang, src)
                counts = collections.Counter(c for _, cs in rows for c in cs)
                self.assertEqual(counts['authenticatedUser'], 1)
                self.assertEqual(counts['getValue'], 1)
                self.assertEqual(sum(n for c,n in counts.items() if c.endswith('subject')), 1)
                self.assertTrue(all(len(cs) == 1 for _,cs in rows))
                for text, cs in rows:
                    if '->getKey' in text: self.assertEqual(cs, ['getKey'])
                    if '?.bar' in text: self.assertEqual(cs, ['bar'])
                    if '!.y' in text: self.assertEqual(cs, ['y'])
                    if '?.Y' in text: self.assertEqual(cs, ['Y'])

    def test_opaque_callees_and_parenthesized_members_keep_their_boundary(self):
        cases = [
            ('javascript', '(function () { document.documentElement.setAttribute("data-theme", theme()); })();',
             [['function'], ['document.documentElement.setAttribute'], ['theme']]),
            ('javascript', 'class A extends B { constructor(props) { super(props); } }', [['super']]),
            ('javascript', '(fn)(); factory()();', [['fn'], ['factory'], ['factory']]),
            ('javascript', '(obj?.method)(); ((obj.method))();', [['method'], ['obj.method']]),
            ('typescript', '(obj!.method)(); ((obj?.method))();', [['method'], ['method']]),
            ('cpp', 'void run() { (ptr->method)(); }', [['method']]),
        ]
        for lang, src, expected in cases:
            with self.subTest(lang=lang,source=src):
                self.assertEqual([cs for _,cs in self._call_candidates(lang,src)],expected)
        payload=self.build({'opaque.js': '(function () { document.documentElement.setAttribute("data-theme", theme()); })(); class A extends B { constructor(props) { super(props); } }'})
        calls=[e for e in payload['edges'] if e['relation']=='calls']
        self.assertTrue(any(e['source']=='opaque.js' and e['target']=='external::function' for e in calls))
        self.assertFalse(any(e['source']=='opaque.js' and e['target']=='external::setAttribute' for e in calls))
        self.assertTrue(any(e['source'].endswith('A.constructor') and e['target']=='external::super' and e['confidence']=='EXTRACTED' for e in calls))


    def test_receiver_and_subscript_controls(self):
        rows = self._call_candidates('swift', 'children[0].getValue()')
        self.assertEqual(rows, [('children[0].getValue()', ['getValue']), ('children[0]', [])])
        for lang, src in [('java','class A { void run(Object e) { e.getKey(); } }'),
                          ('php','<?php $e->getKey();'), ('ruby','e.getKey()'),
                          ('objc','void run(id e) { [e getKey]; }'),
                          ('kotlin','fun run(e: Thing) { e.getKey() }')]:
            with self.subTest(lang=lang):
                self.assertEqual([cs for _,cs in self._call_candidates(lang,src)], [['getKey']])
        # Fifteenth code profile, shell, has no method-member semantics.
        self.assertEqual(self._call_candidates('bash', 'run() { helper; }'), [('helper', ['helper'])])
        art=self.artifact('bash','helper() { echo ok; }\nrun() { helper; }\nrun\n','probe.sh')
        calls=[(e['source'],e['target'],e['confidence']) for e in art['edges'] if e['relation']=='calls']
        self.assertCountEqual(calls,[('probe.sh','probe.sh::run','RECEIVER_RESOLVED'),
                                     ('probe.sh::run','probe.sh::helper','RECEIVER_RESOLVED'),
                                     ('probe.sh::helper','external::echo','EXTRACTED')])

    def test_all_member_profiles_keep_unknown_receiver_confidence(self):
        for lang,(path,src) in PROFILE_FIXTURES.items():
            if lang == 'bash':
                continue  # shell has no member receiver construct
            with self.subTest(lang=lang):
                tree=self.g._ts_parse(lang,src)
                self.assertIsNotNone(tree)
                self.assertFalse(tree.root_node.has_error)
                profile=self.g._TS_LANGUAGE_PROFILES[lang]
                calls=[n for n in walk(tree.root_node) if n.type in profile.call_node_types
                       and 'getValue' in src[n.start_byte:n.end_byte]]
                self.assertTrue(calls)
                self.assertTrue(all(self.g._ts_call_has_receiver(n) for n in calls))
                driver=_RepoDriver(self.g,self.root/lang)
                driver.write(path,src)
                payload=driver.build_incremental({path})
                edges=[e for e in payload['edges'] if e['relation']=='calls' and e['target'].endswith('getValue')]
                self.assertEqual(len(edges),1,edges)
                self.assertEqual(edges[0]['confidence'],'EXTRACTED')
                self.assertTrue(edges[0]['receiver_unknown'])
                # 201wg: confidence alone is not enough; the computed receiver
                # never takes the same-file `getValue` (java, php, scala).
                self.assertEqual(edges[0]['target'],'external::getValue')
                if lang != 'java':  # Java fixture deliberately has a colliding data field.
                    outer=[e for e in payload['edges'] if e['relation']=='calls' and e['target'].endswith('authenticatedUser')]
                    self.assertEqual(len(outer),1,outer)
                    self.assertEqual(outer[0]['confidence'],'EXTRACTED')
                inner=[e for e in payload['edges'] if e['relation']=='calls' and e['target'].endswith('subject')]
                self.assertEqual(len(inner),1,inner)
                self.assertEqual(payload['merge_stats']['non_callable_call_targets'],0)
                self.assertEqual(payload['merge_stats']['malformed_external_call_targets_dropped'],0)

    def test_unknown_import_target_stays_extracted(self):
        payload=self.build({'main.ts': "import { authenticatedUser } from './other'; function run(b: any) { b.subject().authenticatedUser(); }",
                            'other.ts': 'export function authenticatedUser() {}'})
        edges=[e for e in payload['edges'] if e['relation']=='calls' and e['target'].endswith('authenticatedUser')]
        self.assertTrue(edges)
        self.assertTrue(all(e['confidence']=='EXTRACTED' and e.get('receiver_unknown') for e in edges))


    def test_callable_wins_both_constant_orders_and_field_orders(self):
        for first, second in [('static final int hit = 1;', 'int hit() { return 1; }'),
                              ('int hit() { return 1; }', 'static final int hit = 1;'),
                              ('int hit;', 'int hit() { return 1; }'),
                              ('int hit() { return 1; }', 'int hit;')]:
            with self.subTest(first=first):
                src = 'class A {\n' + first + '\n' + second + '\nint read() { return hit; }\nvoid run() { hit(); }\n}'
                art = self.artifact('java',src,'Fixture.java')
                node = next(n for n in art['nodes'] if n['id']=='Fixture.java::A.hit')
                self.assertEqual(node['kind'],'function')
                self.assertEqual(node['source_location'].split(':')[0], '2' if first.startswith('int hit()') else '3')
                self.assertNotIn('value',node)
                self.assertEqual(len(art['callable_wins_collisions']),1)
                self.assertFalse(any(e['relation']=='reads' and e['target']==node['id'] for e in art['edges']))
                self.assertTrue(any(e['relation']=='calls' and e['target']==node['id'] and e['confidence']=='RECEIVER_RESOLVED' for e in art['edges']))
        payload = self.build({'Fixture.java':'class A { static final int hit = 1; int hit() { return 1; } void run() { hit(); } }'})
        self.assertEqual(payload['merge_stats']['callable_wins_collisions'],1)
        self.driver.write('other.py','def other(): return 2\n')
        increment = self.driver.build_incremental({'other.py'})
        oracle = self.driver.build_oracle()
        self.assertEqual(_edge_keys(increment), _edge_keys(oracle))
        self.assertEqual(increment['merge_stats']['callable_wins_collisions'],1)

    def test_scala_val_refused_def_and_construction_kept(self):
        src='class Child {}\nclass Probe { val children = Array.empty[Probe]; def callable(i: Int) = i; def run() = { children(0); callable(0); Child() } }'
        art=self.artifact('scala',src,'Fixture.scala')
        targets=[e['target'] for e in art['edges'] if e['relation']=='calls']
        self.assertNotIn('Fixture.scala::Probe.children',targets)
        self.assertNotIn('external::children',targets)
        self.assertTrue(any(e['target'].endswith('Probe.callable') and e['confidence']=='RECEIVER_RESOLVED' for e in art['edges']))
        self.assertTrue(any(e['target'].endswith('::Child') and e['confidence']=='CONSTRUCTION_RESOLVED' for e in art['edges']))

    def test_java_lexical_visibility_and_unknown_shadow(self):
        src='''class Caller {
 First item;
 void run(Iterable<First> firsts, Iterable<Second> seconds) {
  item.hit();
  for (First item : firsts) { item.hit(); }
  for (Second item : seconds) { item.hit(); }
  item.hit();
  try (Resource item = open()) { item.hit(); }
  catch (Problem item) { item.hit(); }
  item.hit();
  consume((Second item) -> item.hit());
  consume(item -> item.hit());
  item.hit();
 }
}'''
        tree=self.g._ts_parse('java',src);self.assertFalse(tree.root_node.has_error)
        calls=[n for n in walk(tree.root_node) if n.type=='method_invocation' and src[n.start_byte:n.end_byte]=='item.hit()']
        got=[self.g._resolve_java_receiver_type(n,src.encode()) for n in calls]
        self.assertEqual(got,['First','First','Second','First','Resource','Problem','First','Second',None,'First'])
        # Local introduced later cannot capture an earlier reference.
        src='class A { First item; void run() { item.hit(); Second item = open(); item.hit(); } }'
        tree=self.g._ts_parse('java',src)
        got=[self.g._resolve_java_receiver_type(n,src.encode()) for n in walk(tree.root_node) if n.type=='method_invocation' and src[n.start_byte:n.end_byte]=='item.hit()']
        self.assertEqual(got,['First','Second'])

    def test_enhanced_for_iterable_uses_outer_receiver(self):
        payload = self.build({'Fixture.java': '''
class First { Iterable<Second> items() { return null; } }
class Second { void hit() {} }
class Caller {
    First item;
    void run() { for (Second item : item.items()) { item.hit(); } }
}
'''})
        targets = {edge['target'] for edge in payload['edges']
                   if edge['relation'] == 'calls'
                   and edge['source'] == 'Fixture.java::Caller.run'}
        self.assertIn('Fixture.java::First.items', targets)
        self.assertIn('Fixture.java::Second.hit', targets)
        self.assertNotIn('external::Second.items', targets)

    def test_java_visible_types_stay_external_in_public_graph(self):
        src='class Caller { void run(Iterable<Entry> entries) { for (Entry entry : entries) { entry.hit(); } try (Resource resource = open()) { resource.hit(); } catch (Problem error) { error.hit(); } consume((Typed param) -> param.hit()); } }'
        payload=self.build({'Caller.java':src,'Wrong.java':'class Wrong { void hit() {} }'})
        calls=[e for e in payload['edges'] if e['relation']=='calls' and e['source'].endswith('Caller.run') and e['target'].endswith('hit')]
        self.assertEqual({e['target'] for e in calls},{'external::Entry.hit','external::Resource.hit','external::Problem.hit','external::Typed.hit'})
        self.assertTrue(all(e['confidence']=='EXTRACTED' for e in calls))


    def test_java_switch_colon_groups_share_scope_arrow_arms_do_not(self):
        cases=[('class A { Outer item; void run(int i) { switch (i) { case 0: First item = open(); item.hit(); break; case 1: item = open(); item.hit(); break; } item.hit(); } }',
                ['First','First','Outer']),
               ('class A { Outer item; void run(int i) { switch (i) { case 0 -> { First item = open(); item.hit(); } case 1 -> { item.hit(); } } } }',
                ['First','Outer'])]
        for src,expected in cases:
            tree=self.g._ts_parse('java',src)
            self.assertFalse(tree.root_node.has_error)
            calls=[n for n in walk(tree.root_node) if n.type=='method_invocation' and src[n.start_byte:n.end_byte]=='item.hit()']
            self.assertEqual([self.g._resolve_java_receiver_type(n,src.encode()) for n in calls],expected)


    def test_java_later_declarator_and_var_shadow(self):
        src='class A { First later; First item; void run() { Second first = later.hit(), later = open(); var item = open(); item.hit(); } }'
        tree=self.g._ts_parse('java',src)
        self.assertFalse(tree.root_node.has_error)
        calls=[n for n in walk(tree.root_node) if n.type=='method_invocation' and src[n.start_byte:n.end_byte] in ('later.hit()','item.hit()')]
        self.assertEqual([self.g._resolve_java_receiver_type(n,src.encode()) for n in calls],['First',None])


    def test_unknown_receiver_cross_file_and_incremental_ceiling(self):
        caller='class Caller { void run(Object b) { b.subject().authenticatedUser(); helper(); } }'
        payload=self.build({'Caller.java':caller,'Other.java':'class Other { String authenticatedUser() { return ""; } }', 'helper.java':'class Helpers { void helper() {} }'})
        def check(p):
            # 201wg: the computed receiver owns no binding; the unique
            # cross-file name never becomes its target.
            self.assertFalse([e for e in p['edges'] if e['source'].endswith('Caller.run') and e['target'].endswith('Other.authenticatedUser')])
            edges=[e for e in p['edges'] if e['source'].endswith('Caller.run') and e['target']=='external::authenticatedUser']
            self.assertEqual(len(edges),1)
            self.assertEqual(edges[0]['confidence'],'EXTRACTED')
            self.assertTrue(edges[0]['receiver_unknown'])
            self.assertTrue(edges[0]['unowned_member_call'])
        check(payload)
        self.driver.write('Other.java','class Other { String authenticatedUser() { return "new"; } void changed() {} }')
        increment=self.driver.build_incremental({'Other.java'});check(increment)
        oracle=self.driver.build_oracle();check(oracle)
        self.assertEqual(_edge_keys(increment),_edge_keys(oracle))

    def test_extraction_and_fragment_promotion_sites_respect_ceiling(self):
        src="import { authenticatedUser } from './other'; function run(b: any) { b.subject().authenticatedUser(); }"
        self.driver.write('other.ts','export function authenticatedUser() {}')
        art=self.artifact('typescript',src,'main.ts')
        raw=next(e for e in art['edges'] if e['relation']=='calls' and e['target'].endswith('authenticatedUser'))
        self.assertEqual(raw['confidence'],'EXTRACTED')
        self.assertTrue(raw['receiver_unknown'])
        target='Other.java::Other.authenticatedUser'
        nodes={target:{'kind':'function'}}
        ctx={'simple_name_index':{'authenticatedUser':[target]},'qualified_index':{},
             'imports_by_file':{},'cs_file_ns':{},'node_map':nodes}
        raw={'source':'Caller.java::Caller.run','target':'external::authenticatedUser',
             'relation':'calls','confidence':'EXTRACTED','receiver_unknown':True}
        edge=self.g._resolve_fragment_edge(raw,ctx)
        self.assertEqual(edge['target'],target)
        self.assertEqual(edge['confidence'],'EXTRACTED')
        self.assertTrue(self.g._raw_fragment_edge(json.loads(json.dumps(edge)))['receiver_unknown'])
        self.assertTrue(self.g._output_fragment_edge(edge)['receiver_unknown'])
        del raw['receiver_unknown']
        self.assertEqual(self.g._resolve_fragment_edge(raw,ctx)['confidence'],'RECEIVER_RESOLVED')


    def test_receiver_provenance_dedup_and_roundtrip(self):
        key=('a.java::run','external::member','calls','EXTRACTED')
        unknown=dict(zip(('source','target','relation','confidence'),key),receiver_unknown=True)
        known={k:v for k,v in unknown.items() if k!='receiver_unknown'}
        for pair in [(unknown,known),(known,unknown),(unknown,unknown)]:
            edges={}
            for edge in pair:self.g._merge_call_evidence(edges,key,edge)
            stored=json.loads(json.dumps(edges[key]))
            raw=self.g._raw_fragment_edge(stored)
            self.assertEqual(bool(raw.get('receiver_unknown')),pair==(unknown,unknown))

    def test_guess_kind_gate_and_relation_exceptions(self):
        kwargs=dict(simple_name_index={'hit':['A.java::A.hit']},qualified_index={},imports_by_file={},cs_file_ns={},node_map={'A.java::A.hit':{'kind':'variable'}})
        self.assertEqual(self.g._resolve_external_call_target('B.java::B.run','hit','EXTRACTED',**kwargs),(None,False))
        self.assertEqual(self.g._resolve_external_call_target('B.java::B.run','hit','EXTRACTED',relation='writes',**kwargs)[0],'A.java::A.hit')
        kwargs['node_map']['A.java::A.hit']['kind']='function'
        self.assertEqual(self.g._resolve_external_call_target('B.java::B.run','hit','EXTRACTED',**kwargs)[0],'A.java::A.hit')
        del kwargs['node_map']
        with self.assertRaises(TypeError):self.g._resolve_external_call_target('B.java::B.run','hit','EXTRACTED',**kwargs)

    def test_minimal_inheritance_context_kind_gate(self):
        nodes={'A.java::A':{'kind':'class','label':'A'},
               'A.java::A.run':{'kind':'function'},
               'Other.java::Other.hit':{'kind':'variable'}}
        key=('A.java::A.run','external::staticorinherited#A.hit#Other.hit','calls','RECEIVER_RESOLVED')
        edges={key:dict(zip(('source','target','relation','confidence'),key))}
        self.g._apply_inheritance_output_passes(edges,nodes,{}, {'Other.hit':['Other.java::Other.hit']})
        self.assertEqual([e['target'] for e in edges.values()],['external::Other.hit'])
        nodes['Other.java::Other.hit']['kind']='function'
        edges={key:dict(zip(('source','target','relation','confidence'),key))}
        self.g._apply_inheritance_output_passes(edges,nodes,{}, {'Other.hit':['Other.java::Other.hit']})
        self.assertEqual([e['target'] for e in edges.values()],['Other.java::Other.hit'])


    def test_callable_python_constant_is_counted_and_kept(self):
        p=self.build({'a.py':'def build(): return lambda: 1\nHANDLER = build()\ndef run():\n    HANDLER()\n'})
        self.assertTrue(any(e['relation']=='calls' and e['target']=='a.py::HANDLER' for e in p['edges']))
        self.assertEqual(p['merge_stats']['non_callable_call_targets'],1)

    def test_zero_change_preserves_integrity_counts(self):
        p=self.build({'a.py':'def build(): return lambda: 1\nHANDLER = build()\ndef run():\n    HANDLER()\n',
                      'Fixture.java':'class A { static final int hit = 1; int hit() { return 1; } void run() { hit(); } }'})
        self.assertEqual(p['merge_stats']['non_callable_call_targets'],1)
        self.assertEqual(p['merge_stats']['callable_wins_collisions'],1)
        idle=self.driver.build_incremental(set())
        self.assertEqual(idle['merge_stats']['mode'],'zero-change')
        for key in self.g._CALL_INTEGRITY_STATS_KEYS:
            self.assertEqual(idle['merge_stats'][key],p['merge_stats'][key])

    def test_builder_51_cache_reextracts_unchanged_corpus(self):
        src='class A { static final int hit = 1; int hit() { return 1; } void run() { hit(); } }'
        with patch.object(self.g,'GRAPH_BUILDER_VERSION','51'):
            self.build({'Fixture.java':src})
        original=self.g.GraphIndexSession._extract_tree_sitter_artifact
        seen=[]
        def record(session,*args):
            seen.append(args[0]);return original(session,*args)
        with patch.object(self.g.GraphIndexSession,'_extract_tree_sitter_artifact',record):
            payload=self.driver.build_incremental(set())
        self.assertEqual(seen,['Fixture.java'])
        self.assertEqual(payload['builder_version'],self.g.GRAPH_BUILDER_VERSION)
        self.assertEqual(payload['merge_stats']['callable_wins_collisions'],1)


    def test_legacy_arrow_candidate_is_dropped_and_counted(self):
        with patch.object(self.g,'_ts_callee_leaf',lambda node, bs: self.g._ts_clean_name(self.g._ts_node_text(node,bs))):
            payload=self.build({'probe.c':'void run(Thing *e) { e->getKey(); }'})
        self.assertEqual(payload['merge_stats']['malformed_external_call_targets_dropped'],1)
        self.assertFalse(any(e['relation']=='calls' and e['target'].endswith('-') for e in payload['edges']))


    def test_finalize_counts_data_edge_but_drops_malformed(self):
        original=self.g.GraphIndexSession._extract_tree_sitter_artifact
        def inject(session,*args):
            art=original(session,*args)
            art['edges'].extend([{'source':'Fixture.java::A.run','target':'Fixture.java::A.data','relation':'calls','confidence':'RECEIVER_RESOLVED','receiver_unknown':True},
                                 {'source':'Fixture.java::A.run','target':'Fixture.java::A.data','relation':'calls','confidence':'EXTRACTED'},
                                 {'source':'Fixture.java::A.run','target':'external::e-','relation':'calls','confidence':'EXTRACTED'}])
            return art
        with patch.object(self.g.GraphIndexSession,'_extract_tree_sitter_artifact',inject):
            p=self.build({'Fixture.java':'class A { int data; void run() {} }'})
        self.assertEqual(p['merge_stats']['non_callable_call_targets'],1)
        self.assertEqual(p['merge_stats']['malformed_external_call_targets_dropped'],1)
        self.assertTrue(any(e['relation']=='calls' and e['target']=='Fixture.java::A.data' for e in p['edges']))
        self.assertFalse(any(e['relation']=='calls' and e['target']=='external::e-' for e in p['edges']))
        surviving=[e for e in p['edges'] if e['relation']=='calls' and e['target']=='Fixture.java::A.data']
        self.assertEqual(len(surviving),1)
        self.assertNotIn('receiver_unknown',surviving[0])


UNOWNED = 'unowned_member_call'

# 201wg: a computed receiver (call result) collides with a same-file
# function of the method's name. Bare `render()` is the genuine control.
COLLISION_MATRIX = {
    'rust': ('m.rs', 'fn render() {}\nfn run(b: Thing, e: Vec<u8>) { render(); b.subject().render(); e.render(); }\n'),
    'typescript': ('m.ts', 'function render() {} function run(b: any) { render(); b.subject().render(); }'),
    'javascript': ('m.js', 'function render() {} function run(b) { render(); b.subject().render(); }'),
    'go': ('m.go', 'package p\nfunc render() {}\nfunc run(b Thing) { render(); b.subject().render() }\n'),
    'java': ('M.java', 'class P { void render() {} void run(Object b) { render(); b.subject().render(); } }'),
    'kotlin': ('m.kt', 'fun render() {}\nfun run(b: Thing) { render(); b.subject().render() }\n'),
    'swift': ('m.swift', 'func render() {}\nfunc run(b: AnyObject) { render(); b.subject().render() }\n'),
    'scala': ('m.scala', 'class P { def render() = 1; def run(b: P) = { render(); b.subject().render() } }'),
    'csharp': ('m.cs', 'class P { void render() {} void run(dynamic b) { render(); b.subject().render(); } }'),
    'php': ('m.php', '<?php function render() {} function run($b) { render(); $b->subject()->render(); }'),
    'ruby': ('m.rb', 'def render; end\ndef run(b)\n render()\n b.subject().render()\nend\n'),
    'c': ('m.c', 'void render(void) {} void run(Thing *e) { render(); e->render(); }'),
    'cpp': ('m.cpp', 'void render() {} void run(Thing *e, Thing b) { render(); e->render(); b.sub().render(); }'),
    'objc': ('m.m', 'void render(void) {} void run(id b) { render(); [[b sub] render]; }'),
}

RUST_FREE_COLLECT = 'pub fn collect(running: Vec<u32>, started: u64) -> u32 { 0 }\n'
RUST_ITERATOR_CALLER = ('pub fn capture(ids: Vec<u32>) -> Vec<i64> {\n'
                        '    ids.iter().map(|&x| i64::from(x)).collect()\n}\n')
RUST_BARE_CALLER = 'pub fn tally() -> u32 { collect(Vec::new(), 0) }\n'

RUST_CONTROLS = ('struct Thing;\n'
                 'impl Thing {\n'
                 '    fn new() -> Thing { Thing }\n'
                 '    fn make() -> Thing { Thing }\n'
                 '    fn render(&self) {}\n'
                 '    fn run(&self) { self.render(); }\n'
                 '}\n'
                 'fn render() {}\n'
                 'fn drive() { let t: Thing = Thing::make(); t.render(); let u = Thing::new(); render(); a::b::c(); }\n')
TS_CONTROLS = ('class C { static m() {} render() {} run() { this.render(); } }\n'
               'function render() {}\n'
               'function drive() { C.m(); render(); const c = new C(); }\n')


def calls_from(payload, source):
    return sorted((e['target'], e['confidence'], bool(e.get('receiver_unknown')), bool(e.get(UNOWNED)))
                  for e in payload['edges'] if e['relation'] == 'calls' and e['source'] == source)


class UnownedMemberCallTests(unittest.TestCase):
    """201wg: an unowned member call never binds a project callable by name."""

    @classmethod
    def setUpClass(cls):
        cls.g = load_graph_indexer()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.driver = _RepoDriver(self.g, self.root)

    def build(self, files, driver=None):
        driver = driver or self.driver
        for path, src in files.items():
            driver.write(path, src)
        return driver.build_incremental(set(files))

    def artifact(self, lang, src, path):
        session = object.__new__(self.g.GraphIndexSession)
        session.layer = 'project'
        session.root = self.root
        return session._extract_tree_sitter_artifact(path, src, lang)

    def published_edges(self):
        conn = sqlite3.connect(load_index_state_store().state_store_path(self.driver.index_dir))
        try:
            return self.g.read_graph_payload_rows(conn)['edges']
        finally:
            conn.close()

    def assert_unowned(self, edges, source, target='external::collect'):
        hits = [e for e in edges if e['relation'] == 'calls' and e['source'] == source and e['target'] == target]
        self.assertEqual(len(hits), 1, hits)
        self.assertEqual(hits[0]['confidence'], 'EXTRACTED')
        self.assertTrue(hits[0]['receiver_unknown'])
        self.assertTrue(hits[0][UNOWNED])

    def test_rust_same_file_iterator_collect_keeps_unresolved_identity(self):
        src = RUST_FREE_COLLECT + RUST_ITERATOR_CALLER + RUST_BARE_CALLER
        art = self.artifact('rust', src, 'lib.rs')
        self.assertFalse(any(e['source'] == 'lib.rs::capture' and e['target'] == 'lib.rs::collect' for e in art['edges']))
        self.assert_unowned(art['edges'], 'lib.rs::capture')
        payload = self.build({'lib.rs': src})
        for edges in (payload['edges'], self.published_edges()):
            self.assertFalse(any(e['source'] == 'lib.rs::capture' and e['target'] == 'lib.rs::collect' for e in edges))
            self.assert_unowned(edges, 'lib.rs::capture')
            bare = [e for e in edges if e['source'] == 'lib.rs::tally' and e['target'] == 'lib.rs::collect']
            self.assertEqual([(e['confidence'], bool(e.get('receiver_unknown'))) for e in bare], [('RECEIVER_RESOLVED', False)])

    def test_rust_cross_file_iterator_collect_keeps_unresolved_identity(self):
        files = {'src/qualification.rs': RUST_FREE_COLLECT,
                 'src/preprocess.rs': RUST_ITERATOR_CALLER + RUST_BARE_CALLER}
        art = self.artifact('rust', files['src/preprocess.rs'], 'src/preprocess.rs')
        self.assert_unowned(art['edges'], 'src/preprocess.rs::capture')
        payload = self.build(files)
        target = 'src/qualification.rs::collect'
        for edges in (payload['edges'], self.published_edges()):
            self.assertFalse(any(e['source'] == 'src/preprocess.rs::capture' and e['target'] == target for e in edges))
            self.assert_unowned(edges, 'src/preprocess.rs::capture')
            bare = [e for e in edges if e['source'] == 'src/preprocess.rs::tally' and e['target'] == target]
            self.assertEqual([e['confidence'] for e in bare], ['RECEIVER_RESOLVED'])

    def test_member_collision_matrix_is_structural(self):
        for lang, (path, src) in COLLISION_MATRIX.items():
            with self.subTest(lang=lang):
                driver = _RepoDriver(self.g, self.root / lang)
                payload = self.build({path: src}, driver)
                run = next(e['source'] for e in payload['edges']
                           if e['relation'] == 'calls' and e['source'].endswith('run'))
                project = [e for e in payload['edges'] if e['relation'] == 'calls' and e['source'] == run
                           and e['target'].endswith('render') and not e['target'].startswith('external::')]
                # The only project-bound render edge is the genuine bare call.
                self.assertTrue(all(e['confidence'] == 'RECEIVER_RESOLVED' and not e.get('receiver_unknown')
                                    for e in project), project)
                if lang != 'objc':  # this grammar emits no bare-call edge before or after 201wg
                    self.assertEqual(len(project), 1, project)
                self.assert_unowned(payload['edges'], run, 'external::render')

    def test_rust_identifier_receiver_and_cpp_arrow_are_value_syntax(self):
        payload = self.build({'v.rs': 'fn collect() {}\nfn run(items: Vec<u8>) { items.collect(); }\n',
                              'v.cpp': 'void collect() {}\nvoid run(Thing *items) { items->collect(); this->collect(); }\n'})
        self.assert_unowned(payload['edges'], 'v.rs::run', 'external::items.collect')
        self.assert_unowned(payload['edges'], 'v.cpp::run', 'external::collect')
        self.assertFalse(any(e['relation'] == 'calls' and e['target'] == 'v.rs::collect' for e in payload['edges']))
        # `this->` names the enclosing instance and keeps the established bind.
        self.assertTrue(any(e['relation'] == 'calls' and e['source'] == 'v.cpp::run' and e['target'] == 'v.cpp::collect'
                            for e in payload['edges']))

    def assert_owned(self, files, source, target, confidence='EXTRACTED'):
        driver = _RepoDriver(self.g, Path(tempfile.mkdtemp(dir=self.root)))
        payload = self.build(files, driver)
        hits = [e for e in payload['edges'] if e['relation'] == 'calls' and e['source'] == source]
        self.assertEqual([(e['target'], e['confidence'], bool(e.get(UNOWNED))) for e in hits],
                         [(target, confidence, False)], hits)

    def test_ruby_constant_and_scope_receivers_keep_existing_binding(self):
        # DEL-1/DEL-2: a constant path names a module/class, never a value.
        mk = 'module M\n  class K\n    def self.baz; end\n  end\nend\n'
        k = 'class K\n  def self.baz; end\nend\n'
        cases = [('M::K.baz()', {'a.rb': mk}, 'a.rb::M.K.baz'),
                 ('::K.baz()', {'a.rb': k}, 'a.rb::K.baz'),
                 ('K.baz()', {'a.rb': k}, 'a.rb::K.baz'),
                 ('M::K.baz()', {'k.rb': mk}, 'k.rb::M.K.baz'),
                 ('::K.baz()', {'k.rb': k}, 'k.rb::K.baz'),
                 ('K.baz()', {'k.rb': k}, 'k.rb::K.baz')]
        for call, files, target in cases:
            with self.subTest(call=call, files=sorted(files)):
                files = dict(files)
                files['a.rb'] = files.get('a.rb', '') + f'def run\n  {call}\nend\n'
                self.assert_owned(files, 'a.rb::run', target)

    def test_java_qualified_this_keeps_existing_binding(self):
        src = 'class Outer { void foo() {} class Inner { void run() { Outer.this.foo(); } } }'
        self.assert_owned({'Outer.java': src}, 'Outer.java::Outer.Inner.run', 'Outer.java::Outer.foo')

    def test_rust_reference_receivers_resolve_the_named_type(self):
        # DEL-1: `&S` / `&mut S` are stripped to `S`; `let s = S;` names a
        # unit struct. Bounded: a generic reference stays unowned.
        impl = 'pub struct S;\nimpl S { pub fn foo(&self) {} }\n'
        runs = ['fn run(s: &S) { s.foo(); }\n', 'fn run(s: &mut S) { s.foo(); }\n',
                'fn run() { let s = S; s.foo(); }\n', 'fn run(t: S) { let s: &S = &t; s.foo(); }\n']
        for run in runs:
            with self.subTest(run=run, layout='same-file'):
                self.assert_owned({'a.rs': impl + run}, 'a.rs::run', 'a.rs::S.foo', 'RECEIVER_RESOLVED')
            with self.subTest(run=run, layout='cross-file'):
                self.assert_owned({'s.rs': impl, 'a.rs': run}, 'a.rs::run', 's.rs::S.foo', 'RECEIVER_RESOLVED')
        payload = self.build({'g.rs': 'fn collect() {}\nfn run(v: &Vec<u8>, w: &mut u8) { v.collect(); w.collect(); }\n'})
        self.assert_unowned(payload['edges'], 'g.rs::run', 'external::v.collect')
        self.assert_unowned(payload['edges'], 'g.rs::run', 'external::w.collect')

    def test_self_super_and_parenthesized_receivers_keep_existing_binding(self):
        # DEL-2: `super`, `(this)` and `(self)` name the enclosing instance.
        self.assert_owned({'s.ts': 'class B { foo() {} }\nclass A extends B { run() { super.foo(); } }\n'},
                          's.ts::A.run', 's.ts::B.foo')
        self.assert_owned({'p.ts': 'class C { foo() {} run() { (this).foo(); } }\n'}, 'p.ts::C.run', 'p.ts::C.foo')
        self.assert_owned({'p.rs': 'struct S;\nimpl S { fn foo(&self) {} fn run(&self) { (self).foo(); } }\n'},
                          'p.rs::S.run', 'p.rs::S.foo')

    def test_parenthesized_callee_keeps_its_computed_receiver_unowned(self):
        # Delivery reverification: the callee-side paren unwrap must reach the
        # member expression, or the computed receiver binds a same-name function.
        payload = self.build({'m.js': 'function render() {}\nfunction run(b) { (b.subject().render)(); }\n'})
        hits = calls_from(payload, 'm.js::run')
        self.assertIn(('external::render', 'EXTRACTED', True, True), hits)
        self.assertNotIn('m.js::render', [target for target, *_ in hits])

    def test_established_controls_are_unchanged(self):
        for path, src in (('ctl.rs', RUST_CONTROLS), ('ctl.ts', TS_CONTROLS)):
            with self.subTest(path=path):
                fixed = _RepoDriver(self.g, self.root / 'fixed')
                fixed_payload = self.build({path: src}, fixed)
                with patch.object(self.g, '_ts_call_receiver_unowned', lambda node, lang: False):
                    prior = _RepoDriver(self.g, self.root / 'prior')
                    prior_payload = self.build({path: src}, prior)
                self.assertEqual(_edge_keys(fixed_payload), _edge_keys(prior_payload))
                self.assertFalse(any(e.get(UNOWNED) for e in fixed_payload['edges']))
        rust = self.build({'ctl.rs': RUST_CONTROLS})
        drive = calls_from(rust, 'ctl.rs::drive')
        self.assertIn(('ctl.rs::Thing.render', 'RECEIVER_RESOLVED', False, False), drive)
        self.assertIn(('ctl.rs::Thing.make', 'RECEIVER_RESOLVED', False, False), drive)
        self.assertIn(('ctl.rs::render', 'RECEIVER_RESOLVED', False, False), drive)
        self.assertIn(('ctl.rs::Thing', 'CONSTRUCTION_RESOLVED', False, False), drive)
        self.assertIn(('ctl.rs::Thing.render', 'RECEIVER_RESOLVED', False, False), calls_from(rust, 'ctl.rs::Thing.run'))
        ts = self.build({'ctl.ts': TS_CONTROLS})
        self.assertIn(('ctl.ts::C.render', 'RECEIVER_RESOLVED', False, False), calls_from(ts, 'ctl.ts::C.run'))
        drive = calls_from(ts, 'ctl.ts::drive')
        # `C.m()` and `new C()` emit no edge before or after 201wg; the
        # paired prior/fixed comparison above covers them.
        self.assertEqual(drive, [('ctl.ts::render', 'RECEIVER_RESOLVED', False, False)])

    def test_incremental_symbol_transitions_keep_unowned_caller(self):
        caller = 'src/preprocess.rs'
        self.driver.write(caller, RUST_ITERATOR_CALLER)
        self.driver.write('src/bare.rs', RUST_BARE_CALLER)
        steps = [
            ('add', {'src/qualification.rs': RUST_FREE_COLLECT}, set()),
            ('edit', {'src/qualification.rs': RUST_FREE_COLLECT + 'pub fn changed() {}\n'}, set()),
            ('rename', {'src/qualification.rs': RUST_FREE_COLLECT.replace('fn collect', 'fn gather')}, set()),
            ('restore', {'src/qualification.rs': RUST_FREE_COLLECT}, set()),
            ('remove', {}, {'src/qualification.rs'}),
            ('readd', {'src/other.rs': RUST_FREE_COLLECT}, set()),
        ]
        self.driver.build_incremental({caller, 'src/bare.rs'})
        for name, writes, removed in steps:
            with self.subTest(step=name):
                for path, src in writes.items():
                    self.driver.write(path, src)
                for path in removed:
                    self.driver.delete(path)
                increment = self.driver.build_incremental(set(writes), removed)
                oracle = self.driver.build_oracle()
                self.assertEqual(_edge_keys(increment), _edge_keys(oracle))
                for payload in (increment, oracle):
                    self.assert_unowned(payload['edges'], 'src/preprocess.rs::capture')
                    self.assertFalse(any(e['source'] == 'src/preprocess.rs::capture'
                                         and not e['target'].startswith('external::') for e in payload['edges']))
                    bare = [e['target'] for e in payload['edges'] if e['source'] == 'src/bare.rs::tally'
                            and e['relation'] == 'calls' and e['target'].endswith('collect')]
                    expected = {'add': 'src/qualification.rs::collect', 'edit': 'src/qualification.rs::collect',
                                'restore': 'src/qualification.rs::collect', 'readd': 'src/other.rs::collect'}
                    self.assertEqual(bare, [expected.get(name, 'external::collect')])

    def test_fragment_resolution_and_lookup_keys_skip_unowned_edges(self):
        target = 'q.rs::collect'
        ctx = {'simple_name_index': {'collect': [target]}, 'qualified_index': {'items.collect': [target]},
               'imports_by_file': {}, 'cs_file_ns': {}, 'node_map': {target: {'kind': 'function'}}}
        for bare in ('collect', 'items.collect'):
            raw = {'source': 'p.rs::capture', 'target': f'external::{bare}', 'relation': 'calls',
                   'confidence': 'EXTRACTED', 'receiver_unknown': True, UNOWNED: True}
            self.assertEqual(self.g._resolve_fragment_edge(dict(raw), ctx), raw)
            self.assertEqual(self.g._edge_lookup_keys(raw), set())
            unflagged = {k: v for k, v in raw.items() if k != UNOWNED}
            self.assertEqual(self.g._resolve_fragment_edge(unflagged, ctx)['target'], target)
            self.assertTrue(self.g._edge_lookup_keys(unflagged))

    def test_dedup_flag_survives_only_when_every_witness_is_unowned(self):
        key = ('p.java::A.run', 'external::render', 'calls', 'EXTRACTED')
        base = dict(zip(('source', 'target', 'relation', 'confidence'), key))
        unowned = {**base, 'receiver_unknown': True, UNOWNED: True}
        unknown = {**base, 'receiver_unknown': True}
        for pair, flag, receiver in [((unowned, base), False, False), ((base, unowned), False, False),
                                     ((unowned, unknown), False, True), ((unknown, unowned), False, True),
                                     ((unowned, unowned), True, True)]:
            edges = {}
            for edge in pair:
                self.g._merge_call_evidence(edges, key, dict(edge))
            raw = self.g._raw_fragment_edge(json.loads(json.dumps(edges[key])))
            self.assertEqual((bool(raw.get(UNOWNED)), bool(raw.get('receiver_unknown'))), (flag, receiver), pair)

    def test_inheritance_output_pass_skips_unowned_receiver_head(self):
        nodes = {'q.java::items': {'kind': 'class', 'label': 'items'},
                 'q.java::Base': {'kind': 'class', 'label': 'Base'},
                 'q.java::Base.render': {'kind': 'function'}}
        edges_in = {('q.java::items', 'q.java::Base', 'extends', 'RECEIVER_RESOLVED'):
                    {'source': 'q.java::items', 'target': 'q.java::Base', 'relation': 'extends', 'confidence': 'RECEIVER_RESOLVED'}}
        key = ('p.rs::run', 'external::items.render', 'calls', 'EXTRACTED')
        for flagged in (True, False):
            edges = dict(edges_in)
            edge = {**dict(zip(('source', 'target', 'relation', 'confidence'), key)), 'receiver_unknown': True}
            if flagged:
                edge[UNOWNED] = True
            edges[key] = edge
            self.g._apply_inheritance_output_passes(edges, nodes, {'items': ['q.java::items']}, {})
            bound = any(k[0] == 'p.rs::run' and k[1] == 'q.java::Base.render' for k in edges)
            self.assertEqual(bound, not flagged)

    def test_builder_version_transition_replaces_stored_collision(self):
        files = {'src/qualification.rs': RUST_FREE_COLLECT, 'src/preprocess.rs': RUST_ITERATOR_CALLER}
        with patch.object(self.g, 'GRAPH_BUILDER_VERSION', '52'), \
                patch.object(self.g, '_ts_call_receiver_unowned', lambda node, lang: False):
            stale = self.build(files)
        wrong = ('src/preprocess.rs::capture', 'src/qualification.rs::collect')
        self.assertTrue(any((e['source'], e['target']) == wrong for e in stale['edges']))
        self.assertEqual(self.g.read_state_builder_version(self.driver.index_dir), '52')
        payload = self.driver.build_incremental(set())
        self.assertEqual(payload['builder_version'], self.g.GRAPH_BUILDER_VERSION)
        self.assertNotEqual(self.g.GRAPH_BUILDER_VERSION, '52')
        for edges in (payload['edges'], self.published_edges()):
            self.assertFalse(any((e['source'], e['target']) == wrong for e in edges))
            self.assert_unowned(edges, 'src/preprocess.rs::capture')
        self.assertEqual(self.g.read_state_builder_version(self.driver.index_dir), self.g.GRAPH_BUILDER_VERSION)



class RustIdentityProvenanceTests(unittest.TestCase):
    setUpClass = classmethod(CallIntegrityTests.setUpClass.__func__)
    setUp = CallIntegrityTests.setUp
    build = CallIntegrityTests.build
    artifact = CallIntegrityTests.artifact

    def test_trait_impl_identity_and_explicit_calls(self):
        source = '''struct Profile; struct Role;
impl FromStr for Profile { fn from_str() { Self::help(); } }
impl FromStr for Role { fn from_str() {} }
impl Other for Profile { fn from_str() {} }
impl Profile { fn help() {} }
fn run() { <Profile as FromStr>::from_str(); <Role as FromStr>::from_str(); }
'''
        art = self.artifact('rust', source, 'types.rs')
        ids = set(art['defined_symbols'])
        expected = {'types.rs::<Profile as FromStr>.from_str', 'types.rs::<Role as FromStr>.from_str',
                    'types.rs::<Profile as Other>.from_str'}
        self.assertTrue(expected <= ids)
        self.assertNotIn('types.rs::FromStr.from_str', ids)
        calls = {(e['source'], e['target']) for e in art['edges'] if e['relation'] == 'calls'}
        self.assertIn(('types.rs::<Profile as FromStr>.from_str', 'types.rs::Profile.help'), calls)
        for target in expected - {'types.rs::<Profile as Other>.from_str'}:
            self.assertIn(('types.rs::run', target), calls)

    def test_let_initializer_uses_previous_binding_then_new_binding(self):
        source = '''struct P; struct R; struct Mystery;
impl P { fn hit(&self) -> R { R } }
impl R { fn hit(&self) -> R { R } }
fn run(p: P, mystery: Mystery) {
 let p: R = p.hit();
 p.hit();
 { let p: R = p.hit(); p.hit(); }
 let p = mystery; p.hit();
}
fn no_previous() { let p: R = p.hit(); p.hit(); }
'''
        graph = self.build({'types.rs': source})
        sites = {site['start_byte']: edge['target'] for edge in graph['edges']
                 if edge['relation'] == 'calls'
                 for site in edge.get('call_sites', ())
                 if source.encode()[site['start_byte']:site['end_byte']] == b'p.hit()'}
        starts = [m.start() for m in re.finditer(rb'p\.hit\(\)', source.encode())]
        self.assertEqual([sites[start] for start in starts],
                         ['types.rs::P.hit', 'types.rs::R.hit', 'types.rs::R.hit', 'types.rs::R.hit',
                          'external::p.hit', 'external::p.hit', 'types.rs::R.hit'])

    def test_initializer_loop_keeps_outer_array_type(self):
        source = '''struct P; struct R;
impl P { fn hit(&self) {} } impl R { fn hit(&self) {} }
fn run() {
 let values: [P; 1] = [P];
 let values: [R; 1] = { for p in values { p.hit(); } [R] };
 for p in values { p.hit(); }
}
'''
        art = self.artifact('rust', source, 'types.rs')
        calls = [edge for edge in art['edges'] if edge['relation'] == 'calls' and edge['target'].endswith('.hit')]
        self.assertEqual({edge['call_sites'][0]['line']: edge['target'] for edge in calls},
                         {5: 'types.rs::P.hit', 6: 'types.rs::R.hit'})

    def test_explicit_module_receiver_paths_preserve_identity_and_ambiguity(self):
        source = '''trait T { fn hit(&self); } trait U { fn hit(&self); }
mod a { use crate::T; pub struct P; impl T for P { fn hit(&self) {} } }
mod b { use crate::{T,U}; pub struct P; impl T for P { fn hit(&self) {} } impl U for P { fn hit(&self) {} } }
fn run(p: a::P, q: b::P) { a::P::hit(&p); b::P::hit(&q); p.hit(); q.hit(); unknown::P::hit(); }
'''
        graph = self.build({'types.rs': source})
        calls = [edge for edge in graph['edges'] if edge['relation'] == 'calls' and edge['source'] == 'types.rs::run']
        self.assertEqual({edge['target']: len(edge['call_sites']) for edge in calls},
                         {'types.rs::a.<P as T>.hit': 2, 'external::b.P.hit': 2, 'external::unknown.P.hit': 1})
        for edge in calls:
            if edge['target'].startswith('external::'):
                self.assertEqual(edge['confidence'], 'EXTRACTED')

    def test_repeated_bindings_use_bounded_candidate_lookup(self):
        # Count both iteration and indexed access at the real producer boundary.
        # The generous linear bound kills the former N-candidates-per-call scan
        # without a platform-sensitive elapsed-time assertion.
        real_facts = self.g._RustLexicalFacts
        for count in (64, 128, 256):
            visits = [0]
            class Counted(list):
                def __iter__(self):
                    for item in super().__iter__():
                        visits[0] += 1
                        yield item
                def __getitem__(self, key):
                    visits[0] += 1
                    return super().__getitem__(key)
            def instrument(*args):
                facts = real_facts(*args)
                facts.bindings = {scope: {name: Counted(entries) for name, entries in names.items()}
                                  for scope, names in facts.bindings.items()}
                return facts
            source = 'struct P; impl P { fn hit(&self) {} } fn run() {\n' + 'let p: P = P; p.hit();\n' * count + '}'
            with self.subTest(count=count), patch.object(self.g, '_RustLexicalFacts', instrument):
                art = self.artifact('rust', source, 'types.rs')
            sites = [site for edge in art['edges'] if edge['relation'] == 'calls' and edge['target'] == 'types.rs::P.hit'
                     for site in edge['call_sites']]
            self.assertEqual(len(sites), count)
            self.assertEqual(len({site['start_byte'] for site in sites}), count)
            self.assertLessEqual(visits[0], 8 * count)

    def test_generic_impl_identity_retained_but_dispatch_unresolved(self):
        source = "struct P<T>; impl<T> P<T> { fn hit(&self) {} fn run(&self) { self.hit(); Self::hit(); } }"
        art = self.artifact('rust', source, 'types.rs')
        self.assertIn('types.rs::P<T>.hit', art['defined_symbols'])
        calls = [e for e in art['edges'] if e['relation'] == 'calls']
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(e['target'].startswith('external::') for e in calls))
        self.assertTrue(all(e.get('unowned_member_call') for e in calls))

    def test_ambiguous_trait_alias_stays_unresolved(self):
        source = '''struct Profile;
impl One for Profile { fn hit(&self) {} }
impl Two for Profile { fn hit(&self) {} }
fn run(p: Profile) { p.hit(); }
'''
        built = self.build({'types.rs': source})
        calls = [e for e in built['edges'] if e['relation'] == 'calls' and e['source'] == 'types.rs::run']
        self.assertEqual([e['target'] for e in calls], ['external::Profile.hit'])
        self.assertEqual(calls[0]['confidence'], 'EXTRACTED')

    def test_typed_loops_and_lexical_unknown_shadows(self):
        source = '''struct Profile; struct Other;
impl Profile { const ALL: [Self; 2] = []; fn hit(&self) {} fn run() {
 for p in Self::ALL { p.hit(); }
} }
impl Other { fn hit(&self) {} }
fn run(p: Profile, unknown: Mystery) {
 p.hit();
 { let p = unknown; p.hit(); }
 { let p: Other = Other; p.hit(); }
 p.hit();
 let values: [Profile; 2] = [];
 for p in values { p.hit(); }
 for p in unknown { p.hit(); }
 for p in values.iter() { p.hit(); }
 p.hit();
 let p = unknown; p.hit();
}
'''
        art = self.artifact('rust', source, 'types.rs')
        calls = [e for e in art['edges'] if e['relation'] == 'calls' and e['target'].endswith('.hit')]
        targets = {e['call_sites'][0]['line']: e['target'] for e in calls}
        for line in (3, 7, 10, 12, 15):
            self.assertEqual(targets[line], 'types.rs::Profile.hit', line)
        self.assertEqual(targets[9], 'types.rs::Other.hit')
        for line in (8, 13, 14, 16):
            self.assertEqual(targets[line], 'external::p.hit', line)

    def test_later_and_sibling_array_declarations_do_not_leak(self):
        source = '''struct P; impl P { fn hit(&self) {} }
fn run() {
 for p in values { p.hit(); }
 { let values: [P; 2] = []; }
 for p in values { p.hit(); }
 let values: [P; 2] = [];
 for p in values { p.hit(); }
}
'''
        art = self.artifact('rust', source, 'types.rs')
        calls = [e for e in art['edges'] if e['relation'] == 'calls' and e['target'].endswith('.hit')]
        self.assertEqual({e['call_sites'][0]['line']: e['target'] for e in calls},
                         {3: 'external::p.hit', 5: 'external::p.hit', 7: 'types.rs::P.hit'})

    def test_macro_provenance_and_same_line_callers(self):
        source = '''struct P; struct V; impl P { fn hit(&self) {} } impl V { fn hit(&self) {} }
fn first(p: P) { p.hit(); } fn second(v: V, p: P) { println!("é {}", v.hit()); p.hit(); p.hit(); }
'''
        art = self.artifact('rust', source, 'types.rs')
        calls = [e for e in art['edges'] if e['relation'] == 'calls' and e['target'].endswith('.hit')]
        self.assertEqual(len(calls), 4)
        encoded = source.encode()
        for edge in calls:
            site = edge['call_sites'][0]
            expression = encoded[site['start_byte']:site['end_byte']].decode()
            self.assertEqual(expression, 'v.hit()' if edge['target'].endswith('V.hit') else 'p.hit()')
            expected_caller = 'first' if site['start_byte'] < encoded.index(b'fn second') else 'second'
            self.assertEqual(edge['source'], 'types.rs::'+expected_caller)
            line_start = encoded.rfind(b'\n', 0, site['start_byte']) + 1
            self.assertEqual(site['column'], site['start_byte'] - line_start + 1)

    def test_unknown_and_known_witnesses_do_not_share_resolution(self):
        source = '''struct P; impl P { fn hit(&self) {} }
fn run(p: P) { p.hit(); { let p = mystery(); p.hit(); } p.hit(); }
'''
        built = self.build({'types.rs': source})
        calls = [e for e in built['edges'] if e['relation'] == 'calls' and e['source'] == 'types.rs::run' and e['target'].endswith('.hit')]
        by_target = {e['target']: e for e in calls}
        self.assertEqual(len(by_target['types.rs::P.hit']['call_sites']), 2)
        self.assertEqual(len(by_target['external::p.hit']['call_sites']), 1)
        self.assertTrue(by_target['external::p.hit']['unowned_member_call'])

    def test_cross_file_trait_candidates_remain_distinct(self):
        files = {'types.rs': 'struct P; struct R; impl T for P { fn hit() {} } impl T for R { fn hit() {} }',
                 'main.rs': 'fn run() { P::hit(); R::hit(); }'}
        built = self.build(files)
        calls = [e for e in built['edges'] if e['relation'] == 'calls' and e['source'] == 'main.rs::run']
        self.assertEqual({e['target'] for e in calls}, {'types.rs::<P as T>.hit', 'types.rs::<R as T>.hit'})
        self.assertTrue(all(len(e['call_sites']) == 1 for e in calls))


if __name__=='__main__':unittest.main()
