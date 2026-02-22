# পাইথনের অফিশিয়াল লাইটওয়েট ইমেজ ব্যবহার করা হয়েছে
FROM python:3.10-slim

# কন্টেইনারের ভেতরে কাজের ডিরেক্টরি সেট করা
WORKDIR /app

# প্রয়োজনীয় ফাইলগুলো কন্টেইনারে কপি করা
COPY requirements.txt .
COPY bot.py .

# লাইব্রেরিগুলো ইনস্টল করা
RUN pip install --no-cache-dir -r requirements.txt

# বট রান করার কমান্ড
CMD ["python", "cc.py"]