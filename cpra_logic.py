ABO_INCOMPATIBILITY = {
    "A": ["B", "AB"],
    "B": ["A", "AB"],
    "O": ["A", "B", "AB"],
    "AB": [],
}


def build_hla_mask(df, hla_columns: list[str], unacceptable_antigens: list[str]):
    return df[hla_columns].isin(unacceptable_antigens).any(axis=1)


def get_abo_incompatibles(recipient_abo: str) -> list[str]:
    return ABO_INCOMPATIBILITY[recipient_abo]


def build_abo_mask(df, abo_incompatibles: list[str]):
    return df["abo"].isin(abo_incompatibles)


def calc_cpra_filter(mask_hla, df, abo_incompatibles: list[str]) -> float:
    mask_abo = build_abo_mask(df, abo_incompatibles)
    mask_total = mask_hla | mask_abo
    return mask_total.sum() / len(df)


def calc_cpra_freq(cpra_hla: float, frecuencias_abo: dict, abo_incompatibles: list[str]) -> float:
    freq_abo_incomp = sum(frecuencias_abo.get(g, 0) for g in abo_incompatibles)
    return cpra_hla + ((1 - cpra_hla) * freq_abo_incomp)
