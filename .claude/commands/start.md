Bitte nutze folgende Skills zur umsetzung dieses Plans executing-plans, subagent-driven-development. Wir arbeiten strikt nach TDD standards.
Bitte mache entgegen der Anweisung im Skill keine feedbackpausen für den User und setze den Vollständigen Plan um. Arbeite also nicht in batches. Hole dir zwischendrin nur feedback vom User wenn es nötig ist und du ohne eine Entscheidung des Users nicht weitermachen kannst also etwas unklar ist. 

  ---                                                                                                                                                                       
  Test Quality Guidelines                                                                                                                                                   
                                                                                                                                                                            
  Philosophy                                                                                                                                                                
                                                                                                                                                                            
  Tests document expected behavior, not implementation details. A test should answer: "What does this code promise to do?" — not "Which lines did I execute?"               
                                                                                                                                                                            
  Requirements for Every Test                                                                                                                                               
                                                                                                                                                                            
  1. Behavior-First Naming: Test names describe what the system does, not which code path is executed                                                                       
    - ✗ test_branch_297_exit                                                                                                                                                
    - ✗ test_line_156                                                                                                                                                       
    - ✓ test_remove_listener_is_idempotent                                                                                                                                  
    - ✓ test_returns_none_when_no_progress_made                                                                                                                             
  2. Meaningful Assertions: Every test must assert observable behavior                                                                                                      
    - ✗ assert True                                                                                                                                                         
    - ✗ assert x is None or x is not None                                                                                                                                   
    - ✗ Comments like "# Should not crash" without actual assertion                                                                                                         
    - ✓ assert result == expected_value                                                                                                                                     
    - ✓ assert error_callback.was_called_with(expected_error)                                                                                                               
    - ✓ with pytest.raises(ValueError, match="invalid input"):                                                                                                              
  3. Test the Contract, Not the Implementation: Tests should pass even if internal implementation changes                                                                   
    - ✗ Manipulating private attributes (obj._internal_state = ...)                                                                                                         
    - ✗ Asserting on private method calls                                                                                                                                   
    - ✓ Using only public API methods                                                                                                                                       
    - ✓ Monkeypatching external dependencies (time, filesystem, network)                                                                                                    
  4. Regression Value: Ask "Would this test catch a bug?" If the answer is "only if someone deletes this exact line," the test has no value                                 
                                                                                                                                                                            
  Prohibited Patterns                                                                                                                                                       
                                                                                                                                                                            
  # BAD: Tautological assertion                                                                                                                                             
  def test_something():                                                                                                                                                     
      do_something()                                                                                                                                                        
      assert True  # This proves nothing                                                                                                                                    
                                                                                                                                                                            
  # BAD: Line-number driven test                                                                                                                                            
  def test_branch_42_to_45():                                                                                                                                               
      """Cover branch from line 42 to 45."""                                                                                                                                
      ...                                                                                                                                                                   
                                                                                                                                                                            
  # BAD: "Doesn't crash" as only criterion                                                                                                                                  
  def test_edge_case():                                                                                                                                                     
      call_function(None)                                                                                                                                                   
      # Should not crash  <-- This is not a test                                                                                                                            
                                                                                                                                                                            
  # BAD: Private state manipulation for coverage                                                                                                                            
  def test_internal_state():                                                                                                                                                
      obj._private_counter = 5                                                                                                                                              
      obj._start_time = time.time()                                                                                                                                         
      assert obj.some_property  # Fragile, implementation-coupled                                                                                                           
                                                                                                                                                                            
  Required Patterns                                                                                                                                                         
                                                                                                                                                                            
  # GOOD: Behavior-focused with meaningful assertion                                                                                                                        
  def test_estimated_time_requires_progress():                                                                                                                              
      """Estimation returns None until at least one item is processed."""                                                                                                   
      tracker = ProgressTracker(total=10)                                                                                                                                   
      tracker.start()                                                                                                                                                       
                                                                                                                                                                            
      assert tracker.estimated_remaining is None                                                                                                                            
                                                                                                                                                                            
      tracker.update(current=1)                                                                                                                                             
      assert tracker.estimated_remaining is not None                                                                                                                        
      assert tracker.estimated_remaining > 0                                                                                                                                
                                                                                                                                                                            
  # GOOD: Testing error handling behavior                                                                                                                                   
  def test_invalid_input_raises_descriptive_error():                                                                                                                        
      """Users get clear feedback when providing invalid paths."""                                                                                                          
      with pytest.raises(ValueError) as exc_info:                                                                                                                           
          process_path("/nonexistent/path")                                                                                                                                 
                                                                                                                                                                            
      assert "does not exist" in str(exc_info.value)                                                                                                                        
                                                                                                                                                                            
  # GOOD: Using monkeypatch for deterministic tests                                                                                                                         
  def test_rate_calculation(monkeypatch):                                                                                                                                   
      """Processing rate is calculated as items per second."""                                                                                                              
      mock_time = [100.0]                                                                                                                                                   
      monkeypatch.setattr(time, 'time', lambda: mock_time[0])                                                                                                               
                                                                                                                                                                            
      tracker = ProgressTracker(total=10)                                                                                                                                   
      tracker.start()                                                                                                                                                       
                                                                                                                                                                            
      mock_time[0] = 105.0  # 5 seconds elapsed                                                                                                                             
      tracker.update(current=10)                                                                                                                                            
                                                                                                                                                                            
      assert tracker.get_statistics()['average_rate'] == 2.0  # 10 items / 5 sec                                                                                            
                                                                                                                                                                            
  # GOOD: Idempotency/edge case with observable effect                                                                                                                      
  def test_remove_nonexistent_listener_is_safe():                                                                                                                           
      """Removing a listener that was never added has no side effects."""                                                                                                   
      manager = EventManager()                                                                                                                                              
      other_listener = Mock()                                                                                                                                               
                                                                                                                                                                            
      manager.add_listener("event", other_listener)                                                                                                                         
      manager.remove_listener("event", Mock())  # Different listener                                                                                                        
                                                                                                                                                                            
      manager.emit("event")                                                                                                                                                 
      other_listener.assert_called_once()  # Still works                                                                                                                    
                                                                                                                                                                            
  Coverage Philosophy                                                                                                                                                       
                                                                                                                                                                            
  - Coverage is a tool to find untested code, not a goal                                                                                                                    
  - 100% coverage with weak assertions is worse than 80% coverage with strong assertions                                                                                    
  - If a branch is truly unreachable, mark it # pragma: no cover with explanation                                                                                           
  - If covering a branch requires testing implementation details, the code may need refactoring                                                                             
                                                                                                                                                                            
  When Writing Tests, Ask:                                                                                                                                                  
                                                                                                                                                                            
  1. What behavior am I documenting?                                                                                                                                        
  2. If this test fails, what bug does it indicate?                                                                                                                         
  3. Would a new team member understand the expected behavior from this test?                                                                                               
  4. Does this test use only public APIs?                                                                                                                                   
  5. Is my assertion specific enough to catch regressions?                                                                                                                  
      