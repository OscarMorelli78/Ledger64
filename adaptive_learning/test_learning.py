import hashlib,tempfile,unittest
from pathlib import Path
from adaptive_learning.engine import Learner,predict,triage,detect_drift

class LearningTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'memory.db';self.l=Learner(self.path)
 def tearDown(self):self.l.db.close();self.tmp.cleanup()
 def add(self,i,price='100',tenant='a',synthetic=True,reviewer='owner',evidence=None):
  return self.l.observe(tenant,synthetic,str(i),'sku|ud',price,'analyst',reviewer,evidence or hashlib.sha256(str(i).encode()).hexdigest())
 def candidate(self):
  for i in range(30):self.assertTrue(self.add(i,str(99+i%3)))
  return self.l.fit('a',True,'analyst')
 def test_duplicate(self):self.assertTrue(self.add(1));self.assertFalse(self.add(1))
 def test_duplicate_evidence(self):
  self.assertTrue(self.add(1));self.assertFalse(self.add(2,evidence=hashlib.sha256(b'1').hexdigest()))
 def test_bad_price(self):
  for i,p in enumerate(['NaN','Infinity','-1','0','1000000001','garbage']):self.assertFalse(self.add(i,p))
 def test_same_person(self):self.assertFalse(self.add(1,reviewer='analyst'))
 def test_classification(self):self.assertFalse(self.add(1,synthetic=1))
 def test_unknown(self):self.assertIsNone(predict({},'sku|ud',100));self.assertEqual(triage({},'sku|ud',100,3,.4),'unknown')
 def test_invalid_prediction(self):
  m=self.l.model(self.candidate(),'a',True)
  for x in ['NaN','Infinity',0,-5,'bad']:self.assertIsNone(predict(m,'sku|ud',x))
 def test_training(self):
  m=self.l.model(self.candidate(),'a',True);self.assertFalse(predict(m,'sku|ud',100));self.assertTrue(predict(m,'sku|ud',140));self.assertTrue(predict(m,'sku|ud',60))
 def test_tenant(self):
  m=self.candidate();self.assertFalse(self.l.promote(m,'b',True,'owner',True));self.assertEqual(self.l.active('b',True),{})
  with self.assertRaises(ValueError):self.l.model(m,'b',True)
 def test_synthetic(self):
  m=self.candidate();self.assertTrue(self.add(1,'100000',synthetic=False));self.assertFalse(self.l.promote(m,'a',False,'owner',True));self.assertEqual(self.l.active('a',False),{});self.assertAlmostEqual(self.l.model(m,'a',True)['sku|ud'][1],100)
 def test_promotion(self):
  m=self.candidate();self.assertFalse(self.l.promote(m,'a',True,'owner',False));self.assertFalse(self.l.promote(m,'a',True,'analyst',True));self.assertTrue(self.l.promote(m,'a',True,'owner',True));self.assertFalse(self.l.promote(m,'a',True,'owner',True))
 def test_revocation(self):
  m=self.candidate();self.assertTrue(self.l.promote(m,'a',True,'owner',True));self.assertFalse(self.l.revoke('a',True,'0','stranger'));self.assertTrue(self.l.revoke('a',True,'0','owner'));self.assertEqual(self.l.active('a',True),{});self.assertFalse(self.l.promote(m,'a',True,'owner',True));self.assertEqual(self.l.model(self.l.fit('a',True,'analyst'),'a',True)['sku|ud'][0],29)
 def test_restart(self):
  m=self.candidate();self.assertTrue(self.l.promote(m,'a',True,'owner',True));self.l.db.close();self.l=Learner(self.path);self.assertTrue(self.l.verify());self.assertTrue(self.l.active('a',True))
 def test_model_tamper(self):
  m=self.candidate();self.l.db.execute('UPDATE models SET body=? WHERE id=?',('{}',m));self.l.db.commit()
  with self.assertRaises(ValueError):self.l.model(m,'a',True)
 def test_event_tamper(self):
  self.assertTrue(self.add(1));self.l.db.execute("UPDATE events SET body='tampered' WHERE id=1");self.l.db.commit();self.assertFalse(self.l.verify())
 def test_shift_window(self):
  m=self.candidate();self.assertTrue(self.l.promote(m,'a',True,'owner',True))
  for i in range(30,60):self.assertTrue(self.add(i,'130'))
  n=self.l.fit('a',True,'analyst',window=30);self.assertTrue(predict(self.l.active('a',True),'sku|ud',130));self.assertFalse(predict(self.l.model(n,'a',True),'sku|ud',130));self.assertTrue(self.l.promote(n,'a',True,'owner',True));self.assertFalse(predict(self.l.active('a',True),'sku|ud',130))
 def test_drift_monitor(self):
  m=self.l.model(self.candidate(),'a',True);self.assertFalse(detect_drift(m,[('sku|ud',100)]*30)['drift']);self.assertTrue(detect_drift(m,[('sku|ud',130)]*30)['drift']);self.assertFalse(detect_drift(m,[('sku|ud',130)]*10)['drift'])
if __name__=='__main__':unittest.main()
