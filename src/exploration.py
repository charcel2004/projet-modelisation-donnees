import pandas as pd


def profile_dataframe(df, name='jeu de données', max_cardinality=25):
    """Affiche un rapport d'exploration standard. Ne renvoie rien : la fonction affiche."""
    n_rows, n_cols = df.shape

    # 1. Nom, dimensions, empreinte mémoire
    memory_mb = df.memory_usage(deep=True).sum() / 1024 ** 2
    print('=' * 70)
    print(f'RAPPORT : {name}')
    print('=' * 70)
    print(f'Dimensions : {n_rows} lignes x {n_cols} colonnes')
    print(f'Mémoire    : {memory_mb:.2f} Mo')

    # 2. Lignes strictement dupliquées
    n_duplicates = int(df.duplicated().sum())
    print('\n--- lignes dupliquées ---')
    print(f'  {n_duplicates} ligne(s) ({100 * n_duplicates / n_rows:.2f} %)')

    # 3. Tableau par colonne : type, manquants, taux %, valeurs distinctes
    missing = df.isna().sum()
    summary = pd.DataFrame({
        'type': df.dtypes.astype(str),
        'manquants': missing,
        'taux_%': (missing / n_rows * 100).round(2),
        'distincts': df.nunique(),
    })
    print('\n--- colonnes ---')
    print(summary.to_string())

    # 4. Statistiques descriptives des colonnes numériques
    numeric = df.select_dtypes(include='number')
    print('\n--- statistiques numériques ---')
    if numeric.shape[1] == 0:
        print('  aucune colonne numérique')
    else:
        print(numeric.describe().T.round(2).to_string())

    # 5. Répartition des colonnes texte à faible cardinalité
    print(f'\n--- modalités des colonnes texte (< {max_cardinality} valeurs distinctes) ---')
    for column in df.select_dtypes(include=['object', 'string', 'category']).columns:
        n_unique = summary.loc[column, 'distincts']
        if n_unique >= max_cardinality:
            continue
        print(f'\n{column} ({n_unique} modalités)')
        counts = df[column].value_counts(dropna=False)
        for label, count in counts.items():
            print(f'  {label!r:<25} {count:>8}  {100 * count / n_rows:>6.2f} %')