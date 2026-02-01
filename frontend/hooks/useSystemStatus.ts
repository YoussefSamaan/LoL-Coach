import { useState, useEffect } from 'react';

export const useSystemStatus = () => {
    const [systemStatus, setSystemStatus] = useState<'ONLINE' | 'OFFLINE'>('OFFLINE');
    const [version, setVersion] = useState('v0.0.0');

    useEffect(() => {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

        fetch(`${backendUrl}/health`)
            .then(res => res.json())
            .then(data => setSystemStatus(data.status === 'ok' ? 'ONLINE' : 'OFFLINE'))
            .catch(() => setSystemStatus('OFFLINE'));

        fetch(`${backendUrl}/version`)
            .then(res => res.json())
            .then(data => setVersion(`v${data.version}`))
            .catch(() => { });
    }, []);

    return { systemStatus, version };
};
