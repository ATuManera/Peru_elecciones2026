#!/usr/bin/env python3
import argparse, sqlite3, shutil, sys
from pathlib import Path

from project_metadata import build_argument_parser

VALID1_START='000001'
VALID1_END='088064'
MID_START='088065'
MID_END='900000'
VALID2_START='900001'
VALID2_END='904703'

STATUS_PENDING='PENDING'
STATUS_NOT_FOUND='NOT_FOUND'
STATUS_DETAIL_OK='DETAIL_OK'
STATUS_SKIPPED='SKIPPED_ALREADY_DONE'
STATUS_INVALID='INVALID_RESPONSE'
STATUS_FAILED_TEMP='FAILED_TEMP'
STATUS_FAILED_FINAL='FAILED_FINAL'


def q(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def main():
    ap = build_argument_parser(description='Corrige estados del SQLite del scraper ONPE según rangos válidos conocidos.')
    ap.add_argument('--db', default='./data/state/onpe_scraper.sqlite')
    ap.add_argument('--no-backup', action='store_true')
    ap.add_argument('--apply', action='store_true', help='Aplica cambios. Sin esto, solo muestra el plan.')
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f'No existe DB: {db}', file=sys.stderr)
        sys.exit(1)

    if not args.no_backup:
        bak = db.with_suffix(db.suffix + '.pre_fix.bak')
        if not bak.exists():
            shutil.copy2(db, bak)
            print(f'Backup creado: {bak}')
        else:
            print(f'Backup ya existía: {bak}')

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    total = q(conn, 'SELECT COUNT(*) FROM mesas')
    mid_pending = q(conn, 'SELECT COUNT(*) FROM mesas WHERE codigo_mesa BETWEEN ? AND ? AND status = ?', (MID_START, MID_END, STATUS_PENDING))
    mid_other = q(conn, 'SELECT COUNT(*) FROM mesas WHERE codigo_mesa BETWEEN ? AND ? AND status != ?', (MID_START, MID_END, STATUS_NOT_FOUND))
    skipped_with_json = q(conn, 'SELECT COUNT(*) FROM mesas WHERE status = ? AND json_path IS NOT NULL AND json_path != ""', (STATUS_SKIPPED,))
    valid_json_not_ok = q(conn, 'SELECT COUNT(*) FROM mesas WHERE ((codigo_mesa BETWEEN ? AND ?) OR (codigo_mesa BETWEEN ? AND ?)) AND json_path IS NOT NULL AND json_path != "" AND status != ?', (VALID1_START, VALID1_END, VALID2_START, VALID2_END, STATUS_DETAIL_OK))

    print('Resumen previo')
    print('--------------')
    print(f'total filas mesas: {total}')
    print(f'medio rango PENDING {MID_START}-{MID_END}: {mid_pending}')
    print(f'medio rango con estado distinto a NOT_FOUND: {mid_other}')
    print(f'SKIPPED_ALREADY_DONE con json_path: {skipped_with_json}')
    print(f'Rangos válidos con json_path pero status != DETAIL_OK: {valid_json_not_ok}')

    if not args.apply:
        print('\nModo preview. Para aplicar, vuelve a correr con --apply')
        return

    with conn:
        # 1) Todo el tramo vacío conocido pasa a NOT_FOUND y se limpian errores transitorios.
        conn.execute(
            '''UPDATE mesas
               SET status = ?,
                   ultimo_error = NULL,
                   observaciones = TRIM(COALESCE(observaciones,'') || CASE WHEN COALESCE(observaciones,'')='' THEN '' ELSE ' | ' END || 'Corregido por rangos conocidos: sin mesas válidas en 088065-900000')
               WHERE codigo_mesa BETWEEN ? AND ?
                 AND status IN (?, ?, ?, ?)''',
            (STATUS_NOT_FOUND, MID_START, MID_END, STATUS_PENDING, STATUS_FAILED_TEMP, STATUS_FAILED_FINAL, STATUS_INVALID),
        )

        # 2) Cualquier fila con JSON real en rangos válidos debe quedar como DETAIL_OK.
        conn.execute(
            '''UPDATE mesas
               SET status = ?, ultimo_error = NULL
               WHERE ((codigo_mesa BETWEEN ? AND ?) OR (codigo_mesa BETWEEN ? AND ?))
                 AND json_path IS NOT NULL AND json_path != '' ''',
            (STATUS_DETAIL_OK, VALID1_START, VALID1_END, VALID2_START, VALID2_END),
        )

        # 3) Si hubo resumes que marcaron SKIPPED_ALREADY_DONE pero tienen json, devolver a DETAIL_OK.
        conn.execute(
            '''UPDATE mesas
               SET status = ?, ultimo_error = NULL
               WHERE status = ?
                 AND json_path IS NOT NULL AND json_path != '' ''',
            (STATUS_DETAIL_OK, STATUS_SKIPPED),
        )

    print('\nResumen posterior')
    print('-----------------')
    for row in conn.execute('SELECT status, COUNT(*) c FROM mesas GROUP BY status ORDER BY status'):
        print(f"{row['status']}: {row['c']}")

    print('\nChequeos clave')
    print('-------------')
    print('mid range pendientes:', q(conn, 'SELECT COUNT(*) FROM mesas WHERE codigo_mesa BETWEEN ? AND ? AND status = ?', (MID_START, MID_END, STATUS_PENDING)))
    print('mid range not_found:', q(conn, 'SELECT COUNT(*) FROM mesas WHERE codigo_mesa BETWEEN ? AND ? AND status = ?', (MID_START, MID_END, STATUS_NOT_FOUND)))
    print('detail_ok total:', q(conn, 'SELECT COUNT(*) FROM mesas WHERE status = ?', (STATUS_DETAIL_OK,)))
    print('not_found total:', q(conn, 'SELECT COUNT(*) FROM mesas WHERE status = ?', (STATUS_NOT_FOUND,)))


if __name__ == '__main__':
    main()
