import 'package:endless_runner/models/run_config.dart';
import 'package:endless_runner/models/runner.dart';
import 'package:endless_runner/systems/physics.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const c = RunConfig();

  group('Physics.clampDt', () {
    test('clamps a hitch to the max step', () {
      expect(Physics.clampDt(5), Physics.maxStep);
      expect(Physics.clampDt(1 / 60), 1 / 60); // small dt passes through
      expect(Physics.clampDt(-1), 0);
    });
  });

  group('Physics.integrate', () {
    test('a jump rises, gravity falls', () {
      final rising = Physics.integrate(const Runner(vy: 760, grounded: false), 1 / 60, c);
      expect(rising.y, greaterThan(0));
      final falling = Physics.integrate(const Runner(y: 100, grounded: false), 1 / 60, c);
      expect(falling.y, lessThan(100));
    });

    test('landing snaps to the ground and re-grounds', () {
      final landed = Physics.integrate(const Runner(y: 0.001, vy: -1000, grounded: false), 1 / 60, c);
      expect(landed.y, 0);
      expect(landed.vy, 0);
      expect(landed.grounded, isTrue);
    });

    test('a grounded runner stays at rest', () {
      final r = Physics.integrate(const Runner(), 1 / 60, c);
      expect(r.y, 0);
      expect(r.grounded, isTrue);
    });
  });
}
