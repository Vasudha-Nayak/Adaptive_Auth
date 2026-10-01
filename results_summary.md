# Objective 3 Evaluation Summary

Evaluation date: 2026-10-01 20:21:27

## Performance

| Authentication Stage | Mean (ms) | Median (ms) | SD (ms) | P95 (ms) |
|---|---:|---:|---:|---:|
| Password Verification | 785.9830 | 370.9991 | 1134.4620 | 2002.4808 |
| OTP Verification | 0.0002 | 0.0001 | 0.0001 | 0.0004 |
| Face Verification | 0.0002 | 0.0002 | 0.0001 | 0.0002 |
| Session Key Generation | 0.0003 | 0.0003 | 0.0005 | 0.0005 |
| PQC Signing | 10.4955 | 9.9355 | 1.3159 | 13.6344 |
| PQC Verification | 0.4369 | 0.4196 | 0.2005 | 0.7440 |

## Login Scenarios

| Scenario | Server Processing Time (ms) |
|---|---:|
| Static - Normal Login | 785.9830 |
| Adaptive - Normal Login | 796.4791 |
| Adaptive - 1 OTP Retry | 796.4793 |
| Adaptive - 1 Face Retry | 796.4793 |
| Static - 3 Wrong Passwords | 2357.9490 |
| Adaptive - 3 Wrong Passwords | 2357.9490 |

## Cryptographic Integrity

- **backend:** pqcrypto
- **valid_signature:** True
- **modified_message_rejected:** True
- **modified_signature_rejected:** True
- **wrong_public_key_rejected:** True
- **keygen_time_s:** 0.0003125000002910383
- **sign_time_s:** 0.011300699999992503
- **verify_time_s:** 0.00021350000042730244
- **keygen_time_ms:** 0.3125000002910383
- **sign_time_ms:** 11.300699999992503
- **verify_time_ms:** 0.21350000042730244
- **public_key_bytes:** 1952
- **secret_key_bytes:** 4032
- **signature_bytes:** 3309

## Session Key Uniqueness

- Keys generated: 10000
- Unique keys: 10000
- Duplicate keys: 0
- Observed uniqueness: 100.0000%

## Important Methodological Note

Password brute-force and account-takeover probabilities are modeled estimates based on the assumptions in eval_config.py. They should not be reported as experimentally measured attack success rates.

Face ROC analysis is generated only when real face_scores.csv data is supplied.