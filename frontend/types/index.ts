export enum Role {
    TOP = 'TOP',
    JUNGLE = 'JUNGLE',
    MID = 'MID',
    ADC = 'ADC',
    SUPPORT = 'SUPPORT'
}

export interface Champion {
    id: string; // Changed from ChampionId to support dynamic data
    name: string;
    image: string;
}

export interface Recommendation {
    championId: string;
    championName: string;
    score: number;
    primaryReason: string;
}
