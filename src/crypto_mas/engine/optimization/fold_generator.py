from datetime import datetime
from dateutil.relativedelta import relativedelta
from crypto_mas.engine.optimization.schemas import Fold

class FoldGenerator:
    @staticmethod
    def generate_rolling_folds(
        start_date: datetime,
        end_date: datetime,
        train_months: int = 6,
        test_months: int = 2
    ) -> list[Fold]:
        folds = []
        current_train_start = start_date
        fold_id = 1
        
        while True:
            current_train_end = current_train_start + relativedelta(months=train_months)
            current_test_start = current_train_end
            current_test_end = current_test_start + relativedelta(months=test_months)
            
            if current_test_end > end_date:
                # Stop if test period goes beyond available data
                break
                
            folds.append(
                Fold(
                    fold_id=fold_id,
                    train_start=current_train_start,
                    train_end=current_train_end,
                    test_start=current_test_start,
                    test_end=current_test_end
                )
            )
            
            # Slide the window by the test_months to create the next anchored or rolling step.
            # For pure rolling, we shift both start and end. 
            current_train_start += relativedelta(months=test_months)
            fold_id += 1
            
        return folds
