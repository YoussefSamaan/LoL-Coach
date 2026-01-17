import { useState, useEffect } from 'react';
import { Champion } from '@/types';

export const useChampions = () => {
    const [championList, setChampionList] = useState<Champion[]>([]);

    useEffect(() => {
        fetch('https://ddragon.leagueoflegends.com/cdn/14.24.1/data/en_US/champion.json')
            .then(res => res.json())
            .then(data => {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                const list = Object.values(data.data).map((c: any) => ({
                    id: c.id,
                    name: c.name,
                    image: `https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/${c.image.full}`
                }));
                setChampionList(list as Champion[]);
            })
            .catch(err => console.error("Failed to fetch champions", err));
    }, []);

    return championList;
};
