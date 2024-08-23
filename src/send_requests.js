import axios from "axios";

export async function handleEcho(message) {
    try {
        console.log(params)
        const res = await axios.get('http://127.0.0.1:5000/echo', {
            params: { message }
        });
        console.log('hello')
        window.alert(res.data.message);
    } catch (error) {
        console.error('Error fetching the message:', error);
    }
};