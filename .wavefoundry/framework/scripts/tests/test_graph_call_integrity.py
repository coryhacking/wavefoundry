"""1xtnr: calls preserve callable identity, receiver evidence and callee syntax."""
from __future__ import annotations
import collections
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from test_graph_incremental_merge import _RepoDriver, _edge_keys, load_graph_indexer
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
            edges=[e for e in p['edges'] if e['source'].endswith('Caller.run') and e['target'].endswith('Other.authenticatedUser')]
            self.assertEqual(len(edges),1)
            self.assertEqual(edges[0]['confidence'],'EXTRACTED')
            self.assertTrue(edges[0]['receiver_unknown'])
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
        self.assertEqual(payload['builder_version'],'52')
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


if __name__=='__main__':unittest.main()
