import { useState, useEffect } from 'react';

export const useSystemStatus = () => {
    const [systemStatus, setSystemStatus] = useState<'ONLINE' | 'OFFLINE'>('OFFLINE');
    const [version, setVersion] = useState('v0.0.0');

    useEffect(() => {
        fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/health`)
            .then(res => res.json())
            .then(data => setSystemStatus(data.status === 'ok' ? 'ONLINE' : 'OFFLINE'))
            .catch(() => setSystemStatus('OFFLINE'));

        fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/version`)
            .then(res => res.json())
            .then(data => setVersion(`v${data.version}`))
            .catch(() => { });
    }, []);

    return { systemStatus, version };
};
