
import chess
from database import SessionLocal
from models import Puzzle, Chapter

# Ground truth: (fen, solution_san, solution_uci) — verified positions + Stockfish depth-20 solutions
ground_truth = {
    1:  ("8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1",                    "Rf6+",   "f3f6"),
    2:  ("r2qk2r/ppp2ppp/2np4/8/3Pn3/2P1B3/PP2NPPP/R2QK2R w KQkq - 0 1",      "d5",     "d4d5"),
    3:  ("r2qk2r/ppp2ppp/2n1b3/2b5/2BpP3/8/PPPN1PPP/R1BQ1RK1 w kq - 0 1",     "Bxe6",   "c4e6"),
    4:  ("1k6/ppq4p/5r2/4Q3/8/4N1P1/P5PP/7K w - - 0 1",                        "Qxf6",   "e5f6"),
    5:  ("8/p3br1k/1p4pp/2pq4/6N1/1P3P2/P3Q1PP/5RK1 w - - 0 1",               "Qxe7",   "e2e7"),
    6:  ("r2q1rk1/ppp2ppp/2nb4/4n3/4P3/2NP4/PP1B2PP/R2Q1RK1 w - - 0 1",       "d4",     "d3d4"),
    7:  ("8/p1r1k2r/1p5q/4Pp2/1P1Q2p1/6P1/3R1PK1/5R2 w - - 0 1",              "Qd8+",   "d4d8"),
    8:  ("3r4/4q1kp/r1p1ppp1/2p5/2P5/1P2PQ1P/5PP1/3R1RK1 w - - 0 1",          "Rxd8",   "d1d8"),
    9:  ("r6k/pp3Qpp/2bqp3/4Np2/2P5/8/PP3PPP/5RK1 w - - 0 1",                 "Qxb7",   "f7b7"),
    10: ("6k1/1q4p1/5p1p/2Pnn2Q/3p4/6P1/2r2PNP/5RK1 w - - 0 1",              "h3",     "h2h3"),
    11: ("2r4k/6pp/1b1p4/3Q4/5q2/2B5/5PP1/5RK1 w - - 0 1",                    "Bxg7+",  "c3g7"),
    12: ("r5k1/ppq2p1p/2n3p1/8/3N3r/8/PP1Q1PPP/5RK1 w - - 0 1",               "Nf3",    "d4f3"),
    13: ("3b1r2/5pk1/4p1p1/2qpP1Np/B4Q1P/8/5PP1/6K1 w - - 0 1",               "Qxf7+",  "f4f7"),
    14: ("Q7/p4rkp/3q2p1/4p1N1/P1P5/6P1/7P/7K w - - 0 1",                     "Qh8+",   "a8h8"),
    15: ("r3r1k1/p3qpp1/3b3p/2p5/2P5/1P6/P1B1Q1PP/3R1RK1 w - - 0 1",          "Qd3",    "e2d3"),
    16: ("r4rk1/pp1bq1pp/5p2/1Bbp4/8/2P3BP/PP2Q1P1/R4RK1 w - - 0 1",          "Bf2",    "g3f2"),
    17: ("r3k2r/p1p3p1/n3Nq1p/4pP2/8/2P3P1/PP2B1PP/4K2R w Kkq - 0 1",         "Bxa6",   "e2a6"),
    18: ("r5k1/p4bp1/1p3n2/5p1q/4pP2/2N2P2/P2QB1PP/5RK1 w - - 0 1",           "fxe4",   "f3e4"),
    19: ("7k/2p3pp/1p3q2/2n1N3/8/P5P1/1P3PBP/3R2K1 w - - 0 1",                "Rd8+",   "d1d8"),
    20: ("r3k2r/1p2bpp1/p1n1p2p/q7/3P4/3B1Q2/PP2NPPP/2R2RK1 w kq - 0 1",      "Rxc6",   "c1c6"),
    21: ("1r4k1/3q1pp1/5b1p/1p1P4/8/1B1Q3P/5PP1/5RK1 w - - 0 1",              "g3",     "g2g3"),
    22: ("r5k1/p5pp/1q3n2/1p1p4/1P6/P1B2Q1P/5PP1/5RK1 w - - 0 1",             "Bxf6",   "c3f6"),
    23: ("2br1bk1/6p1/1p6/2p1pp2/8/qN3P2/P1Q2BPP/5RK1 w - - 0 1",             "Qc4+",   "c2c4"),
    24: ("k7/pp4p1/7p/3Nq3/2P2n2/1P6/5PPP/R5K1 w - - 0 1",                    "Nb6+",   "d5b6"),
    25: ("7k/5p1p/p5p1/3q4/P3p1P1/4P1QP/2r2PK1/8 w - - 0 1",                  "a5",     "a4a5"),
    26: ("2k5/1p5p/p4n2/3Rpq2/2PN4/1P5P/5B1P/6K1 w - - 0 1",                  "Rc5+",   "d5c5"),
    27: ("r1bq1rk1/p1p1bppp/1p2pn2/6B1/3P4/3B1N2/PPP1QPPP/R3K2R w KQ - 0 1", "Bxf6",   "g5f6"),
    28: ("7k/p1r2p1p/q3n3/Q1P1p3/3pP3/3P2P1/5B1P/1R4K1 w - - 0 1",            "Qxa6",   "a5a6"),
    29: ("8/1b3pkp/pn1p2p1/3Pq3/Q3P3/8/6PP/6K1 b - - 0 1",                    "Nxa4",   "b6a4"),
    30: ("5nk1/4rppp/p7/2pqNQ2/8/P3P2P/5PP1/4R1K1 w - - 0 1",                 "Ng6",    "e5g6"),
    31: ("7k/ppp1rRbp/4q1p1/3pn3/3P4/2P2QP1/PP4P1/6K1 w - - 0 1",             "Rf8+",   "f7f8"),
    32: ("r1b2rk1/2q2p1p/p1p1pQ2/1p6/8/P2B3P/1P3PP1/R4RK1 w - - 0 1",         "Qg5+",   "f6g5"),
    33: ("6k1/1p3ppn/7p/7b/1r6/3Q2PP/2P2PK1/8 w - - 0 1",                     "Qd8+",   "d3d8"),
    34: ("8/r4Pk1/3p2pp/8/p4B2/r4NP1/6KP/3R4 w - - 0 1",                      "f8=Q+",  "f7f8q"),
    35: ("8/pp3kPR/2n5/8/4Npq1/P1N3P1/1P4K1/8 w - - 0 1",                     "g8=Q+",  "g7g8q"),
    36: ("2r2rk1/4pp1p/3p2p1/3P4/3qPP2/1N2n2P/5QP1/2RR3K b - - 0 1",          "Qxe4",   "d4e4"),
    37: ("3k3r/1q4bp/p2Np1pB/3pn3/1p4PP/6Q1/PPP5/1K1R4 w - - 0 1",            "Nxb7+",  "d6b7"),
    38: ("7k/p4p2/6p1/3q4/6N1/2P4P/5PP1/1R4K1 w - - 0 1",                     "Rb8+",   "b1b8"),
    39: ("1k1r4/p1p5/7p/6p1/4n3/b2B1Q1P/2P3P1/1K6 b - - 0 1",                 "Nd2+",   "e4d2"),
    40: ("6k1/1p4p1/p1n1q2p/1np5/p2P4/2P2rB1/1P5P/K4N1R b - - 0 1",           "cxd4",   "c5d4"),
    41: ("3r4/8/p2q1Qpk/5p2/5N2/4P3/P4P1P/6K1 w - - 0 1",                     "Qh4+",   "f6h4"),
    42: ("r1b1k2r/pp3ppp/4p3/1Nqpn3/8/2P1P3/PP2BPPP/R2Q1RK1 w kq - 0 1",      "Qd4",    "d1d4"),
    43: ("5rk1/5p1p/3Q2p1/pp1N2q1/7n/1P5P/P4PP1/5RK1 w - - 0 1",              "Nf6+",   "d5f6"),
    44: ("r6k/r7/8/1p2pp1P/3n4/R3BP2/6PK/3R4 w - - 0 1",                      "Rxa7",   "a3a7"),
    45: ("1r3r2/7k/5p1p/4N1PP/1p3b2/1P6/2R1BP2/6K1 w - - 0 1",                "Rc7+",   "c2c7"),
    46: ("1k1r4/pP2q3/8/Q5pP/5bP1/5P1K/P1R5/8 w - - 0 1",                     "Rc8+",   "c2c8"),
    47: ("7Q/pq1P1kp1/4n3/6p1/1P2p1P1/P4P2/6K1/8 w - - 0 1",                  "Qe8+",   "h8e8"),
    48: ("8/6p1/2n1k2p/1np5/p2P4/2P2rB1/1P5P/K4N1R w - - 0 1",                "d5+",    "d4d5"),
    49: ("r4rk1/pp2ppbp/6p1/8/Qnq1P3/2N1BPP1/PP4KP/R4R2 b - - 0 1",           "Bxc3",   "g7c3"),
    50: ("4r1k1/4r3/2p5/2Bp3p/3P1p1B/1Q6/8/6K1 b - - 0 1",                    "Rg7+",   "e7g7"),
}

def insert_truth():
    db = SessionLocal()
    try:
        # Clear existing puzzles for Chapter 1
        db.query(Puzzle).filter_by(chapter_id=1).delete()

        inserted = 0
        for pnum, (fen, solution_san, solution_uci) in ground_truth.items():
            pdf_page = 13 + ((pnum - 1) // 3)
            p = Puzzle(
                chapter_id=1,
                puzzle_number=pnum,
                fen=fen,
                turn=fen.split()[1],
                solution_san=solution_san,
                solution_uci=solution_uci,
                pdf_page=pdf_page,
                verified=1,
                extraction_confidence=1.0
            )
            db.add(p)
            inserted += 1

        chapter = db.query(Chapter).get(1)
        if chapter:
            chapter.puzzle_count = inserted

        db.commit()
        print(f"Inserted {inserted} ground truth puzzles.")
    finally:
        db.close()

if __name__ == "__main__":
    insert_truth()
