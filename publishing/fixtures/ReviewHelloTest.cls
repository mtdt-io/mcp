@IsTest
private class ReviewHelloTest {
    @IsTest
    static void returnsReviewMessage() {
        System.assertEquals('MTDT review fixture', ReviewHello.message());
    }
}
